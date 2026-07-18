"""
Metrics Route.

Exposes Prometheus metrics for scraping.
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["observability"])

@router.get("/metrics", include_in_schema=False)
async def get_metrics() -> Response:
    """
    Prometheus scraping endpoint.
    
    Exposed at /api/v1/metrics. This endpoint is typically called by a Prometheus 
    server running in the cluster (e.g. every 15 seconds).
    
    Not included in the OpenAPI schema because it's an internal infrastructure route.
    """
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )
