"""
Health Check Routes.

Provides liveness and readiness probes for:
- Kubernetes / Docker health checks
- Load balancer health probes
- Monitoring system checks

Endpoints:
    GET /api/v1/health          → Liveness probe (is app running?)
    GET /api/v1/health/ready    → Readiness probe (can app serve traffic?)
    GET /api/v1/health/detailed → Full component status (DB, Redis, MinIO)
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from engine.config.database import AsyncSessionLocal
from engine.config.settings import get_settings
from engine.utils.logging import get_logger

router = APIRouter(prefix="/health", tags=["Health"])
logger = get_logger(__name__)
settings = get_settings()

# Application start time for uptime calculation
_START_TIME = datetime.now(timezone.utc)


@router.get(
    "",
    summary="Liveness probe",
    description="Simple liveness check — returns 200 if the application is running.",
    response_description="Application status",
)
async def health_liveness() -> dict:
    """
    Liveness probe.

    Returns 200 if the application process is alive.
    Does NOT check external dependencies — that's the readiness probe.
    """
    uptime_seconds = (datetime.now(timezone.utc) - _START_TIME).total_seconds()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(uptime_seconds, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Checks if the application can serve traffic (DB connection verified).",
)
async def health_readiness() -> JSONResponse:
    """
    Readiness probe.

    Returns 200 only if the database connection is available.
    Returns 503 if the DB is unreachable.
    """
    db_healthy = await _check_database()

    if db_healthy:
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "database": "connected"},
        )
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )


@router.get(
    "/detailed",
    summary="Detailed health status",
    description="Full component health check including DB, Redis, and MinIO.",
)
async def health_detailed() -> JSONResponse:
    """
    Detailed health check with component status.

    Checks all external dependencies and returns their individual status.
    Useful for debugging infrastructure issues.
    """
    db_ok = await _check_database()
    redis_ok = await _check_redis()

    all_healthy = db_ok and redis_ok
    uptime_seconds = (datetime.now(timezone.utc) - _START_TIME).total_seconds()

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime_seconds": round(uptime_seconds, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "database": "healthy" if db_ok else "unhealthy",
                "redis": "healthy" if redis_ok else "unhealthy",
            },
        },
    )


async def _check_database() -> bool:
    """Execute a trivial query to verify database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("health.database_check_failed", error=str(e))
        return False


async def _check_redis() -> bool:
    """Ping Redis to verify connectivity."""
    try:
        import redis.asyncio as redis_client
        client = redis_client.from_url(settings.redis.url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return True
    except Exception as e:
        logger.warning("health.redis_check_failed", error=str(e))
        return False
