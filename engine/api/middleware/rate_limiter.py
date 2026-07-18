"""
API Rate Limiting Middleware.

Uses Redis to enforce rate limits per tenant (or IP if unauthenticated).
Implements a basic Fixed Window algorithm.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from engine.config.settings import get_settings
from engine.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Default limits (Requests per minute)
DEFAULT_LIMIT_AUTHENTICATED = 1000
DEFAULT_LIMIT_UNAUTHENTICATED = 60

# Paths excluded from rate limiting
EXCLUDED_PATHS = {"/api/v1/health", "/api/v1/metrics", "/api/v1/openapi.json"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Redis-backed Rate Limiting Middleware.
    
    Limits are enforced per tenant_id (if authenticated) or client IP.
    """

    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        # Create a connection pool for rate limiting
        self.redis = Redis.from_url(settings.redis.url, decode_responses=True)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and enforce rate limits."""
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # Determine identifier and limit
        tenant_id = getattr(request.state, "tenant", None)
        if tenant_id:
            identifier = f"tenant:{tenant_id.id}"
            limit = DEFAULT_LIMIT_AUTHENTICATED
        else:
            client_ip = self._get_client_ip(request)
            identifier = f"ip:{client_ip}"
            limit = DEFAULT_LIMIT_UNAUTHENTICATED

        # Fixed Window rate limiting
        current_minute = int(time.time() // 60)
        redis_key = f"rate_limit:{identifier}:{current_minute}"

        try:
            # Increment and set expiry in a pipeline
            pipe = self.redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 60)  # Expire key after 1 minute
            result = await pipe.execute()
            request_count = result[0]

            if request_count > limit:
                logger.warning(
                    "http.rate_limited",
                    identifier=identifier,
                    path=request.url.path,
                    count=request_count,
                    limit=limit
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "RateLimitExceeded",
                        "message": f"Too many requests. Limit is {limit} per minute.",
                    },
                    headers={"Retry-After": "60"},
                )

            # Process request
            response = await call_next(request)
            
            # Attach rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - request_count))
            response.headers["X-RateLimit-Reset"] = str((current_minute + 1) * 60)
            
            return response

        except Exception as e:
            # If Redis fails, fail open (do not block traffic)
            logger.error("rate_limiter.redis_failure", error=str(e))
            return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
