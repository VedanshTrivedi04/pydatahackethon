"""
Prometheus Metrics Middleware.

Tracks HTTP request counts and durations.
Exposes these metrics to Prometheus scrapers.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# -------------------------------------------------------------------
# Prometheus Metrics Definitions
# -------------------------------------------------------------------

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to intercept every request and record Prometheus metrics.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Record start time, execute request, record duration and status.
        """
        method = request.method
        
        # We group endpoints by route template (e.g., /api/v1/jobs/{job_id}) 
        # instead of the raw path to avoid cardinality explosion in Prometheus.
        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            # If an unhandled exception bubbles up, it usually results in a 500
            status_code = "500"
            raise
        finally:
            duration = time.perf_counter() - start_time
            
            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

        return response
