"""
Tenant Repository — Infrastructure Layer.

Responsible for ALL database queries related to tenants and their secrets.

Design principles:
- Repository Pattern: all SQL lives here, nowhere else
- Service layer calls repository methods — never raw SQLAlchemy outside this file
- All queries include soft-delete filters (deleted_at IS NULL)
- All queries are tenant-scoped where applicable

This is the ONLY place that talks to the tenants / tenant_secrets tables.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from engine.core.models.tenant import Tenant, TenantSecret


class TenantRepository:
    """
    Data access object for Tenant and TenantSecret entities.

    All methods are async and accept an AsyncSession injected by the service layer.
    Never instantiate this with a permanent session — always pass the
    request-scoped session from the FastAPI dependency.

    Args:
        session: The async SQLAlchemy session for this request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -------------------------------------------------------------------------
    # Tenant Secret Lookups (used in auth hot path)
    # -------------------------------------------------------------------------

    async def get_secret_by_key_hash(
        self, key_hash: str
    ) -> TenantSecret | None:
        """
        Look up a TenantSecret by its key hash.

        This is the auth hot path — called on every authenticated request.
        The query is indexed on key_hash for sub-millisecond lookups.

        Args:
            key_hash: SHA-256 hex digest of the raw API key.

        Returns:
            The TenantSecret if found and active, None otherwise.
        """
        stmt = (
            select(TenantSecret)
            .where(
                TenantSecret.key_hash == key_hash,
                TenantSecret.is_active.is_(True),
                TenantSecret.deleted_at.is_(None),
            )
            .options(selectinload(TenantSecret.tenant))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tenant_with_active_key(
        self, key_hash: str
    ) -> Tenant | None:
        """
        Resolve a Tenant from an API key hash in a single query.

        Joins tenant_secrets → tenants, applying all active/non-deleted filters.
        Returns the Tenant directly (already loaded via the join).

        Args:
            key_hash: SHA-256 hex digest of the raw API key.

        Returns:
            Active Tenant if the key is valid, None otherwise.
        """
        stmt = (
            select(Tenant)
            .join(TenantSecret, TenantSecret.tenant_id == Tenant.id)
            .where(
                TenantSecret.key_hash == key_hash,
                TenantSecret.is_active.is_(True),
                TenantSecret.deleted_at.is_(None),
                Tenant.is_active.is_(True),
                Tenant.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_secret_last_used(self, secret_id: uuid.UUID) -> None:
        """
        Update the last_used_at timestamp on a TenantSecret.

        Called after successful authentication to track key usage.
        Uses a targeted UPDATE — does not load the full object.

        Args:
            secret_id: UUID of the TenantSecret to update.
        """
        stmt = (
            update(TenantSecret)
            .where(TenantSecret.id == secret_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self._session.execute(stmt)

    # -------------------------------------------------------------------------
    # Tenant CRUD
    # -------------------------------------------------------------------------

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        """
        Fetch a single tenant by primary key.

        Args:
            tenant_id: UUID of the tenant.

        Returns:
            Tenant if found and not soft-deleted, None otherwise.
        """
        stmt = (
            select(Tenant)
            .where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        """
        Fetch a tenant by its unique slug.

        Args:
            slug: URL-safe unique identifier.

        Returns:
            Tenant if found, None otherwise.
        """
        stmt = (
            select(Tenant)
            .where(
                Tenant.slug == slug,
                Tenant.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> list[Tenant]:
        """
        List all tenants with optional active filter and pagination.

        Args:
            limit:       Max number of results (default 50, max 200).
            offset:      Pagination offset.
            active_only: If True, exclude inactive tenants.

        Returns:
            List of Tenant instances.
        """
        stmt = select(Tenant).where(Tenant.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(Tenant.is_active.is_(True))
        stmt = stmt.order_by(Tenant.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, tenant: Tenant) -> Tenant:
        """
        Persist a new Tenant to the database.

        Args:
            tenant: A Tenant instance (not yet added to session).

        Returns:
            The persisted Tenant with generated ID and timestamps.
        """
        self._session.add(tenant)
        await self._session.flush()  # Flush to get DB-generated values
        await self._session.refresh(tenant)
        return tenant

    async def create_secret(self, secret: TenantSecret) -> TenantSecret:
        """
        Persist a new TenantSecret to the database.

        Args:
            secret: A TenantSecret instance (not yet added to session).

        Returns:
            The persisted TenantSecret with generated ID.
        """
        self._session.add(secret)
        await self._session.flush()
        await self._session.refresh(secret)
        return secret

    async def list_secrets_for_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[TenantSecret]:
        """
        List all API keys for a tenant (active and inactive).

        Note: Returns metadata only — key_hash is NOT exposed in API responses.
        Only key_prefix and name are safe to return to the user.

        Args:
            tenant_id: UUID of the owning tenant.

        Returns:
            List of TenantSecret instances ordered by creation date.
        """
        stmt = (
            select(TenantSecret)
            .where(
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.deleted_at.is_(None),
            )
            .order_by(TenantSecret.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def revoke_secret(self, secret_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """
        Revoke an API key by marking it inactive.

        Verifies tenant ownership before revoking — prevents cross-tenant key revocation.

        Args:
            secret_id: UUID of the TenantSecret to revoke.
            tenant_id: UUID of the tenant making the request (ownership check).

        Returns:
            True if revoked, False if not found or not owned by this tenant.
        """
        stmt = (
            update(TenantSecret)
            .where(
                TenantSecret.id == secret_id,
                TenantSecret.tenant_id == tenant_id,
                TenantSecret.deleted_at.is_(None),
            )
            .values(is_active=False)
            .returning(TenantSecret.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def update_tenant(
        self, tenant_id: uuid.UUID, **fields: object
    ) -> Tenant | None:
        """
        Update specific fields on a Tenant record.

        Args:
            tenant_id: UUID of the tenant to update.
            **fields:  Field name/value pairs to update.

        Returns:
            Updated Tenant or None if not found.
        """
        stmt = (
            update(Tenant)
            .where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
            .values(**fields)
            .returning(Tenant)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, tenant_id: uuid.UUID) -> bool:
        """
        Soft-delete a tenant by setting deleted_at.

        Also deactivates all their API keys to prevent further authentication.

        Args:
            tenant_id: UUID of the tenant.

        Returns:
            True if deleted, False if not found.
        """
        now = datetime.now(timezone.utc)
        # Soft-delete the tenant
        tenant_stmt = (
            update(Tenant)
            .where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
            .values(deleted_at=now, is_active=False)
            .returning(Tenant.id)
        )
        result = await self._session.execute(tenant_stmt)
        if result.scalar_one_or_none() is None:
            return False

        # Deactivate all secrets for this tenant
        secrets_stmt = (
            update(TenantSecret)
            .where(TenantSecret.tenant_id == tenant_id)
            .values(is_active=False, deleted_at=now)
        )
        await self._session.execute(secrets_stmt)
        return True
