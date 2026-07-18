"""
FastAPI Dependencies — Authentication & Tenant Resolution.

These are the route-level guards that enforce authentication
on protected endpoints.

Usage in routes:
    from engine.api.dependencies.auth import get_current_tenant

    @router.get("/jobs")
    async def list_jobs(
        tenant: Tenant = Depends(get_current_tenant),
        db: AsyncSession = Depends(get_db_session),
    ):
        ...

The `get_current_tenant` dependency:
1. Checks if middleware already resolved the tenant (request.state.tenant)
2. If yes, return it — zero extra DB calls
3. If no (middleware wasn't run or failed), attempt fresh resolution
4. If neither — raise 401
"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from engine.config.database import get_db_session
from engine.core.auth.bearer import bearer_extractor
from engine.core.models.tenant import Tenant, TenantSecret
from engine.core.tenants.repository import TenantRepository
from engine.core.tenants.service import TenantService
from engine.utils.exceptions import AuthenticationError
from engine.utils.logging import get_logger

logger = get_logger(__name__)


async def get_tenant_service(
    session: AsyncSession = Depends(get_db_session),
) -> TenantService:
    """
    FastAPI dependency that provides a TenantService bound to the request session.

    Args:
        session: Async DB session (request-scoped).

    Returns:
        TenantService instance for this request.
    """
    repo = TenantRepository(session)
    return TenantService(session=session, repository=repo)


async def get_current_tenant(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Tenant:
    """
    FastAPI dependency that resolves and returns the authenticated tenant.

    Priority:
    1. Use request.state.tenant if middleware already resolved it (fast path)
    2. Attempt fresh resolution from Authorization header (fallback)
    3. Raise AuthenticationError if neither succeeds

    This dependency is the SINGLE gate for all protected routes.
    Any route with `Depends(get_current_tenant)` requires valid auth.

    Args:
        request: Current HTTP request.
        session: Async DB session for fresh resolution if needed.

    Returns:
        The resolved active Tenant.

    Raises:
        AuthenticationError: Converted to HTTP 401 by the exception handler.
    """
    # Fast path — middleware already resolved the tenant
    if getattr(request.state, "authenticated", False) and request.state.tenant:
        return request.state.tenant  # type: ignore[return-value]

    # Fallback path — middleware didn't run or failed (shouldn't happen in production)
    # Resolve from Authorization header directly
    try:
        extracted = await bearer_extractor.extract(request)
    except ValueError as e:
        raise AuthenticationError(str(e)) from e

    repo = TenantRepository(session)
    service = TenantService(session=session, repository=repo)

    try:
        tenant, secret = await service.resolve_tenant_from_key(extracted.raw_key)
        # Attach to request state for audit logging downstream
        request.state.tenant = tenant
        request.state.tenant_secret = secret
        request.state.authenticated = True
        return tenant
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error("auth.dependency.unexpected_error", error=str(e))
        raise AuthenticationError("Authentication failed.") from e


async def get_current_tenant_and_secret(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> tuple[Tenant, TenantSecret]:
    """
    Like get_current_tenant but also returns the TenantSecret.

    Used in endpoints that need to know WHICH API key was used
    (e.g. for audit logging, key usage tracking).

    Args:
        request: Current HTTP request.
        session: Async DB session.

    Returns:
        Tuple of (Tenant, TenantSecret).
    """
    tenant = await get_current_tenant(request, session)
    secret: TenantSecret = request.state.tenant_secret
    return tenant, secret
