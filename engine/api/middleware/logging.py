"""
Request Logging Middleware.

Intercepts every HTTP request/response to:
1. Generate a unique request_id (UUID)
2. Extract correlation_id from client header (X-Correlation-ID)
3. Bind context to structlog for the request lifetime
4. Measure request latency
5. Log request/response details in structured format
6. Add X-Request-ID to response headers

This middleware is the observability backbone — every log line
during a request will automatically include request_id and tenant_id.
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from engine.utils.logging import bind_request_context, clear_request_context, get_logger

logger = get_logger(__name__)

# Paths to exclude from detailed logging (too noisy)
LOG_SKIP_PATHS = {"/api/v1/health", "/api/v1/metrics"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured request/response logging middleware.

    Wraps every HTTP request with:
    - Unique request_id injected into headers and logs
    - Latency measurement
    - Structured log entry per request
    - Automatic structlog context binding/clearing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request with logging and correlation tracking.
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Extract client-provided correlation ID (for distributed tracing)
        correlation_id = request.headers.get("X-Correlation-ID", request_id)

        # Attach to request state for downstream access
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        # Bind to structlog context — all log calls in this request get these
        tenant_id = None
        if hasattr(request.state, "tenant") and request.state.tenant:
            tenant_id = str(request.state.tenant.id)

        bind_request_context(
            request_id=request_id,
            tenant_id=tenant_id,
        )

        # Record start time
        start_time = time.perf_counter()

        # Log incoming request (skip noisy health paths)
        if request.url.path not in LOG_SKIP_PATHS:
            logger.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                client_ip=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:200],
            )

        # Process the request
        response = await call_next(request)

        # Calculate latency
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Log response (skip noisy health paths)
        if request.url.path not in LOG_SKIP_PATHS:
            log_fn = logger.warning if response.status_code >= 400 else logger.info
            log_fn(
                "http.response",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                latency_ms=latency_ms,
            )

        # Inject request ID into response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        # Clear structlog context (important — prevents context leakage between requests)
        clear_request_context()

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extract the real client IP, handling reverse proxy forwarded headers.
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can be "client, proxy1, proxy2"
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
