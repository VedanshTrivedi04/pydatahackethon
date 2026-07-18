"""
Authentication Middleware.

Runs on every request BEFORE it reaches route handlers.
Responsible for:
1. Extracting the Bearer API key from the Authorization header
2. Resolving the tenant via TenantService
3. Attaching the resolved tenant to request.state for downstream use

This middleware does NOT block non-authenticated routes (health, docs, webhooks).
The FastAPI dependency `get_current_tenant` enforces auth on specific routes.

Design: Middleware does discovery; dependency enforces the requirement.
"""

from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from engine.core.auth.bearer import bearer_extractor
from engine.core.auth.hasher import hash_api_key, is_valid_key_format
from engine.utils.logging import get_logger

logger = get_logger(__name__)

# Routes that bypass authentication resolution entirely
AUTH_BYPASS_PREFIXES = (
    "/api/v1/health",
    "/api/v1/docs",
    "/api/v1/openapi.json",
    "/api/v1/redoc",
    "/webhooks/",         # Webhooks use their own signature verification
)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Soft authentication middleware.

    On every request:
    - If Authorization: Bearer is present → attempt tenant resolution
    - If valid → attach tenant + secret to request.state
    - If invalid → attach nothing (route dependency will enforce auth if required)
    - If bypass path → skip entirely

    This "soft" approach means unauthenticated requests can still reach
    public routes (health, docs, webhooks) without middleware blocking them.
    Authenticated routes use the `get_current_tenant` dependency instead.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through soft auth resolution.
        """
        # Initialize state attributes
        request.state.tenant = None
        request.state.tenant_secret = None
        request.state.authenticated = False
        request.state.user_id = None
        request.state.user_role = None

        # Skip auth resolution for bypass paths
        if any(request.url.path.startswith(prefix) for prefix in AUTH_BYPASS_PREFIXES):
            return await call_next(request)

        # Attempt to extract and resolve API key or JWT
        try:
            extracted = await bearer_extractor.extract(request)
            raw_token = extracted.raw_key

            # Import here to avoid circular imports at module level
            from engine.config.database import AsyncSessionLocal
            from engine.core.tenants.repository import TenantRepository
            from engine.core.tenants.service import TenantService
            from engine.core.auth.jwt import decode_access_token

            # 1. JWT Authentication (Human User)
            if raw_token.startswith("ey"):
                payload = decode_access_token(raw_token)
                if payload:
                    user_id = payload.get("sub")
                    request.state.user_id = user_id
                    
                    # For JWTs, the frontend must explicitly specify which tenant they are acting on
                    # via the X-Tenant-ID header.
                    target_tenant_id = request.headers.get("X-Tenant-ID")
                    
                    if target_tenant_id:
                        async with AsyncSessionLocal() as session:
                            # Verify the user actually belongs to this tenant
                            from sqlalchemy import select
                            from engine.core.models.tenant_member import TenantMember
                            from engine.core.models.tenant import Tenant
                            
                            stmt = (
                                select(Tenant, TenantMember.role)
                                .join(TenantMember, TenantMember.tenant_id == Tenant.id)
                                .where(
                                    TenantMember.user_id == user_id,
                                    TenantMember.tenant_id == target_tenant_id
                                )
                            )
                            result = await session.execute(stmt)
                            row = result.first()
                            
                            if row:
                                request.state.tenant = row[0]
                                request.state.user_role = row[1]
                                request.state.authenticated = True

            # 2. API Key Authentication (Machine-to-Machine)
            elif raw_token.startswith("sf_"):
                async with AsyncSessionLocal() as session:
                    repo = TenantRepository(session)
                    service = TenantService(session=session, repository=repo)
                    tenant, secret = await service.resolve_tenant_from_key(raw_token)
                    
                    request.state.tenant = tenant
                    request.state.tenant_secret = secret
                    request.state.authenticated = True
                    request.state.user_role = "owner"  # API Keys act as tenant owners by default

        except Exception:
            # Soft failure — don't block the request here
            # The route-level dependency will return 401 if auth is required
            pass

        return await call_next(request)
