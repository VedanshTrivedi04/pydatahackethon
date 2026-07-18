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

        # Skip auth resolution for bypass paths
        if any(request.url.path.startswith(prefix) for prefix in AUTH_BYPASS_PREFIXES):
            return await call_next(request)

        # Attempt to extract and resolve API key
        try:
            extracted = await bearer_extractor.extract(request)

            # Import here to avoid circular imports at module level
            from engine.config.database import AsyncSessionLocal
            from engine.core.tenants.repository import TenantRepository
            from engine.core.tenants.service import TenantService

            async with AsyncSessionLocal() as session:
                repo = TenantRepository(session)
                service = TenantService(session=session, repository=repo)
                tenant, secret = await service.resolve_tenant_from_key(extracted.raw_key)

            request.state.tenant = tenant
            request.state.tenant_secret = secret
            request.state.authenticated = True

        except Exception:
            # Soft failure — don't block the request here
            # The route-level dependency will return 401 if auth is required
            pass

        return await call_next(request)
