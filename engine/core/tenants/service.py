"""
Tenant Service — Service Layer.

Orchestrates all tenant-related business logic:
- Tenant creation (with first API key)
- API key generation and revocation
- Tenant resolution from API key (auth path)
- Tenant profile updates

This is the ONLY layer above the repository.
FastAPI routes and middleware call this service — never the repository directly.

Depends on:
    TenantRepository (injected via constructor)
    AuditService (injected via constructor, for audit logging)
"""

import uuid
import re

from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.auth.hasher import (
    generate_api_key,
    hash_api_key,
    is_valid_key_format,
    verify_api_key,
)
from engine.core.models.tenant import Tenant, TenantSecret
from engine.core.tenants.repository import TenantRepository
from engine.utils.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


# Slug validation regex — lowercase alphanumeric + hyphens only
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{2,98}[a-z0-9]$")


class TenantService:
    """
    Business logic for all tenant and API key operations.

    Instantiated per-request via FastAPI dependency injection.
    The session and repository are scoped to the current request.

    Args:
        session:    Async SQLAlchemy session (request-scoped).
        repository: TenantRepository instance for this session.
    """

    def __init__(
        self,
        session: AsyncSession,
        repository: TenantRepository,
    ) -> None:
        self._session = session
        self._repo = repository

    # -------------------------------------------------------------------------
    # Authentication / Tenant Resolution
    # -------------------------------------------------------------------------

    async def resolve_tenant_from_key(self, raw_key: str) -> tuple[Tenant, TenantSecret]:
        """
        Authenticate a request by resolving the tenant from a raw API key.

        Process:
        1. Fast format check (rejects garbage before hitting DB)
        2. Hash the raw key
        3. Look up TenantSecret by hash
        4. Verify key is active and tenant is active
        5. Update last_used_at on the secret (non-blocking intent)

        Args:
            raw_key: The plaintext key from the Authorization header.

        Returns:
            Tuple of (Tenant, TenantSecret) — both guaranteed active.

        Raises:
            AuthenticationError: If the key is invalid, expired, or the tenant
                                 is inactive. Returns a generic message to prevent
                                 information leakage.
        """
        # 1. Format check — fast rejection before DB lookup
        if not is_valid_key_format(raw_key):
            raise AuthenticationError("Invalid API key format.")

        # 2. Hash the key
        key_hash = hash_api_key(raw_key)

        # 3. DB lookup — single query joining secrets → tenants
        secret = await self._repo.get_secret_by_key_hash(key_hash)

        if secret is None:
            # Generic message — don't reveal whether tenant or key doesn't exist
            raise AuthenticationError("Invalid or expired API key.")

        # 4. Validate key expiry
        if secret.expires_at is not None:
            from datetime import datetime, timezone
            if datetime.now(timezone.utc) > secret.expires_at:
                raise AuthenticationError("API key has expired.")

        # 5. Validate tenant is active (eagerly loaded via selectinload)
        tenant = secret.tenant
        if tenant is None or not tenant.is_active:
            raise AuthenticationError("Tenant account is suspended or not found.")

        # 6. Update last_used_at (best-effort — don't fail auth if this fails)
        try:
            await self._repo.update_secret_last_used(secret.id)
        except Exception:
            pass  # Non-critical — log but don't fail auth

        return tenant, secret

    # -------------------------------------------------------------------------
    # Tenant CRUD
    # -------------------------------------------------------------------------

    async def create_tenant(
        self,
        name: str,
        slug: str,
        email: str | None = None,
        plan: str = "free",
        initial_key_name: str = "Default Key",
    ) -> tuple[Tenant, str]:
        """
        Create a new tenant with their first API key.

        Atomically creates:
        - The Tenant record
        - One TenantSecret (hashed key)

        Returns the tenant AND the raw API key (plaintext, shown once).

        Args:
            name:            Human-readable org name.
            slug:            URL-safe unique identifier.
            email:           Optional contact email.
            plan:            Subscription plan (free | pro | enterprise).
            initial_key_name: Label for the first API key.

        Returns:
            Tuple of (Tenant, raw_api_key).
            The raw_api_key must be shown to the user — it will never be retrievable again.

        Raises:
            ValidationError:  If slug format is invalid.
            ConflictError:    If the slug is already taken.
        """
        # Validate slug format
        self._validate_slug(slug)

        # Check slug uniqueness
        existing = await self._repo.get_by_slug(slug)
        if existing is not None:
            raise ConflictError(f"Tenant slug '{slug}' is already in use.")

        # Create tenant record
        tenant = Tenant(
            name=name,
            slug=slug,
            email=email,
            plan=plan,
            is_active=True,
        )
        tenant = await self._repo.create(tenant)

        # Generate and store first API key
        raw_key, key_hash, key_prefix = generate_api_key()
        secret = TenantSecret(
            tenant_id=tenant.id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=initial_key_name,
            is_active=True,
        )
        await self._repo.create_secret(secret)

        return tenant, raw_key

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        """
        Fetch a single tenant by ID.

        Args:
            tenant_id: UUID of the tenant.

        Returns:
            Tenant entity.

        Raises:
            NotFoundError: If tenant doesn't exist or is soft-deleted.
        """
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise NotFoundError(f"Tenant '{tenant_id}' not found.")
        return tenant

    async def list_tenants(
        self,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> list[Tenant]:
        """
        List all tenants with pagination.

        Args:
            limit:       Max results (capped at 200 internally).
            offset:      Pagination offset.
            active_only: Exclude inactive tenants.

        Returns:
            List of Tenant entities.
        """
        capped_limit = min(limit, 200)
        return await self._repo.get_all(limit=capped_limit, offset=offset, active_only=active_only)

    async def update_tenant(
        self,
        tenant_id: uuid.UUID,
        **updates: object,
    ) -> Tenant:
        """
        Update allowed fields on a tenant.

        Only whitelisted fields may be updated — prevents mass assignment.

        Args:
            tenant_id: UUID of the tenant to update.
            **updates: Fields to update (name, email, viasocket_webhook_url, plan).

        Returns:
            Updated Tenant entity.

        Raises:
            NotFoundError:   If tenant not found.
            ValidationError: If attempting to update disallowed fields.
        """
        allowed_fields = {"name", "email", "viasocket_webhook_url", "plan", "github_app_installation_id"}
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise ValidationError(f"Cannot update fields: {', '.join(invalid_fields)}")

        updated = await self._repo.update_tenant(tenant_id, **updates)
        if updated is None:
            raise NotFoundError(f"Tenant '{tenant_id}' not found.")
        return updated

    async def deactivate_tenant(self, tenant_id: uuid.UUID) -> None:
        """
        Soft-delete a tenant and revoke all their API keys.

        Args:
            tenant_id: UUID of the tenant.

        Raises:
            NotFoundError: If tenant not found.
        """
        deleted = await self._repo.soft_delete(tenant_id)
        if not deleted:
            raise NotFoundError(f"Tenant '{tenant_id}' not found.")

    # -------------------------------------------------------------------------
    # API Key Management
    # -------------------------------------------------------------------------

    async def create_api_key(
        self,
        tenant_id: uuid.UUID,
        name: str | None = None,
    ) -> tuple[TenantSecret, str]:
        """
        Generate a new API key for an existing tenant.

        Args:
            tenant_id: UUID of the owning tenant.
            name:      Optional label for this key.

        Returns:
            Tuple of (TenantSecret metadata, raw_api_key).
            Store only the TenantSecret — raw_api_key is shown once.

        Raises:
            NotFoundError: If tenant not found.
        """
        # Verify tenant exists
        tenant = await self._repo.get_by_id(tenant_id)
        if tenant is None:
            raise NotFoundError(f"Tenant '{tenant_id}' not found.")

        raw_key, key_hash, key_prefix = generate_api_key()
        secret = TenantSecret(
            tenant_id=tenant_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            is_active=True,
        )
        secret = await self._repo.create_secret(secret)
        return secret, raw_key

    async def revoke_api_key(
        self,
        secret_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> None:
        """
        Revoke an API key belonging to a specific tenant.

        Ownership check prevents cross-tenant key revocation.

        Args:
            secret_id: UUID of the TenantSecret to revoke.
            tenant_id: UUID of the requesting tenant (ownership assertion).

        Raises:
            NotFoundError: If key not found or not owned by this tenant.
        """
        revoked = await self._repo.revoke_secret(secret_id, tenant_id)
        if not revoked:
            raise NotFoundError(
                f"API key '{secret_id}' not found or not owned by this tenant."
            )

    async def list_api_keys(self, tenant_id: uuid.UUID) -> list[TenantSecret]:
        """
        List all API keys for a tenant.

        Args:
            tenant_id: UUID of the tenant.

        Returns:
            List of TenantSecret instances (without key_hash — never expose this).
        """
        return await self._repo.list_secrets_for_tenant(tenant_id)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_slug(slug: str) -> None:
        """
        Validate slug format: lowercase alphanumeric + hyphens, 4-100 chars.

        Args:
            slug: The slug to validate.

        Raises:
            ValidationError: If the slug doesn't match the required pattern.
        """
        if not SLUG_PATTERN.match(slug):
            raise ValidationError(
                "Tenant slug must be 4-100 characters, lowercase alphanumeric and hyphens only, "
                "must start and end with alphanumeric character."
            )
