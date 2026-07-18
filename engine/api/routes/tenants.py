"""
Tenant API Routes — /api/v1/tenants

Handles tenant registration, profile management, and API key CRUD.

Route summary:
    POST   /api/v1/tenants                     → Create tenant + first API key
    GET    /api/v1/tenants                     → List tenants (admin)
    GET    /api/v1/tenants/{tenant_id}         → Get tenant profile
    PATCH  /api/v1/tenants/{tenant_id}         → Update tenant profile
    DELETE /api/v1/tenants/{tenant_id}         → Soft-delete tenant
    GET    /api/v1/tenants/{tenant_id}/keys    → List API keys
    POST   /api/v1/tenants/{tenant_id}/keys    → Create new API key
    DELETE /api/v1/tenants/{tenant_id}/keys/{key_id} → Revoke API key

Auth: All routes except POST /tenants (registration) require authentication.
      Tenants can only manage their own data.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from engine.api.dependencies.auth import get_current_tenant, get_tenant_service
from engine.api.schemas.tenant import (
    APIKeyMetadata,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    CreateTenantRequest,
    CreateTenantResponse,
    TenantDetailSchema,
    TenantListResponse,
    TenantResponse,
    TenantSchema,
    UpdateTenantRequest,
)
from engine.config.database import get_db_session
from engine.core.models.tenant import Tenant
from engine.core.tenants.repository import TenantRepository
from engine.core.tenants.service import TenantService
from engine.utils.exceptions import PermissionError
from engine.utils.logging import get_logger

router = APIRouter(prefix="/tenants", tags=["Tenants"])
logger = get_logger(__name__)


# =============================================================================
# Tenant Registration (Public — no auth required)
# =============================================================================

@router.post(
    "",
    response_model=CreateTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new tenant",
    description=(
        "Creates a new tenant organization and returns their first API key. "
        "**The API key is shown ONLY once — store it securely immediately.**"
    ),
)
async def create_tenant(
    body: CreateTenantRequest,
    service: TenantService = Depends(get_tenant_service),
) -> CreateTenantResponse:
    """Register a new tenant and return their first API key."""
    tenant, raw_key = await service.create_tenant(
        name=body.name,
        slug=body.slug,
        email=str(body.email) if body.email else None,
        plan=body.plan,
        initial_key_name=body.initial_key_name,
    )

    # Get the created key metadata for the response
    keys = await service.list_api_keys(tenant.id)
    key_meta = keys[0] if keys else None

    logger.info(
        "tenant.created",
        tenant_id=str(tenant.id),
        slug=tenant.slug,
        plan=tenant.plan,
    )

    return CreateTenantResponse(
        success=True,
        tenant=TenantSchema.model_validate(tenant),
        api_key=raw_key,
        key_metadata=APIKeyMetadata.model_validate(key_meta),
    )


# =============================================================================
# Tenant Listing (Admin — protected)
# =============================================================================

@router.get(
    "",
    response_model=TenantListResponse,
    summary="List all tenants (admin only)",
    description="Returns a paginated list of all tenants. Requires admin-level access.",
)
async def list_tenants(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = True,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> TenantListResponse:
    """List tenants — admin only (plan=enterprise check or separate admin key)."""
    # Simple admin gate: only enterprise plan tenants can list all tenants
    if current_tenant.plan != "enterprise":
        raise PermissionError("Only enterprise plan tenants can list all tenants.")

    tenants = await service.list_tenants(limit=limit, offset=offset, active_only=active_only)
    return TenantListResponse(
        success=True,
        tenants=[TenantSchema.model_validate(t) for t in tenants],
        total=len(tenants),
        limit=limit,
        offset=offset,
    )


# =============================================================================
# Single Tenant Operations
# =============================================================================

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant profile",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    """Fetch a tenant's profile. Tenants can only view their own profile."""
    _assert_own_tenant(current_tenant.id, tenant_id)
    tenant = await service.get_tenant(tenant_id)
    return TenantResponse(success=True, tenant=TenantSchema.model_validate(tenant))


@router.patch(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant profile",
)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: UpdateTenantRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> TenantResponse:
    """Update a tenant's profile. Tenants can only update their own profile."""
    _assert_own_tenant(current_tenant.id, tenant_id)

    updates = body.model_dump(exclude_none=True)
    if not updates:
        # No fields provided — return current state
        return TenantResponse(success=True, tenant=TenantSchema.model_validate(current_tenant))

    tenant = await service.update_tenant(tenant_id, **updates)

    logger.info("tenant.updated", tenant_id=str(tenant_id), fields=list(updates.keys()))

    return TenantResponse(success=True, tenant=TenantSchema.model_validate(tenant))


@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate tenant",
)
async def deactivate_tenant(
    tenant_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> None:
    """Soft-delete a tenant and revoke all their API keys."""
    _assert_own_tenant(current_tenant.id, tenant_id)
    await service.deactivate_tenant(tenant_id)
    logger.info("tenant.deactivated", tenant_id=str(tenant_id))


# =============================================================================
# API Key Management
# =============================================================================

@router.get(
    "/{tenant_id}/keys",
    response_model=dict,
    summary="List API keys",
)
async def list_api_keys(
    tenant_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> dict:
    """List all API keys for a tenant. Returns metadata only — no key hashes."""
    _assert_own_tenant(current_tenant.id, tenant_id)
    keys = await service.list_api_keys(tenant_id)
    return {
        "success": True,
        "keys": [APIKeyMetadata.model_validate(k).model_dump() for k in keys],
        "total": len(keys),
    }


@router.post(
    "/{tenant_id}/keys",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    tenant_id: uuid.UUID,
    body: CreateAPIKeyRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> CreateAPIKeyResponse:
    """Generate a new API key for this tenant. Shown ONCE — save it immediately."""
    _assert_own_tenant(current_tenant.id, tenant_id)
    secret, raw_key = await service.create_api_key(tenant_id=tenant_id, name=body.name)

    logger.info(
        "api_key.created",
        tenant_id=str(tenant_id),
        key_prefix=secret.key_prefix,
    )

    return CreateAPIKeyResponse(
        success=True,
        api_key=raw_key,
        metadata=APIKeyMetadata.model_validate(secret),
    )


@router.delete(
    "/{tenant_id}/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def revoke_api_key(
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    service: TenantService = Depends(get_tenant_service),
) -> None:
    """Revoke an API key. The key will immediately become invalid."""
    _assert_own_tenant(current_tenant.id, tenant_id)
    await service.revoke_api_key(secret_id=key_id, tenant_id=tenant_id)
    logger.info(
        "api_key.revoked",
        tenant_id=str(tenant_id),
        key_id=str(key_id),
    )


# =============================================================================
# Private Helpers
# =============================================================================

def _assert_own_tenant(current_id: uuid.UUID, target_id: uuid.UUID) -> None:
    """
    Assert that the authenticated tenant is acting on their own resource.

    Raises PermissionError if the IDs don't match — prevents cross-tenant access.

    Args:
        current_id: The authenticated tenant's UUID.
        target_id:  The tenant UUID being accessed.
    """
    if current_id != target_id:
        raise PermissionError(
            "You do not have permission to access this tenant's resources."
        )
