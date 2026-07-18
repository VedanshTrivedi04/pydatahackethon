"""
ShipFaster — FastAPI Application Entry Point.

This is the root of the ASGI application. It:
1. Creates the FastAPI app with versioned API docs
2. Registers all middleware (order matters — outermost first)
3. Registers all exception handlers
4. Includes all route modules
5. Manages application lifespan (startup/shutdown)

Running:
    uvicorn engine.api.main:app --reload --port 8000

The OpenAPI schema is auto-generated at:
    GET /api/v1/openapi.json   → Dev 2 uses this for typed client generation
    GET /api/v1/docs           → Swagger UI
    GET /api/v1/redoc          → ReDoc UI
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from engine.api.exceptions.handlers import register_exception_handlers
from engine.api.middleware.auth import AuthMiddleware
from engine.api.middleware.logging import RequestLoggingMiddleware
from engine.api.routes import health, tenants, jobs, webhooks, artifacts
from engine.config.settings import get_settings
from engine.utils.logging import configure_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Runs setup code on startup and teardown code on shutdown.
    This replaces the deprecated @app.on_event("startup") pattern.
    """
    # ---------------------------------------------------------------
    # STARTUP
    # ---------------------------------------------------------------
    configure_logging()
    logger.info(
        "shipfaster.startup",
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )

    # Verify DB connection on startup
    try:
        from sqlalchemy import text
        from engine.config.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("shipfaster.database_connected")
    except Exception as e:
        logger.error("shipfaster.database_connection_failed", error=str(e))
        # Don't crash on startup — let health endpoint report the issue

    yield  # Application is running

    # ---------------------------------------------------------------
    # SHUTDOWN
    # ---------------------------------------------------------------
    logger.info("shipfaster.shutdown")
    from engine.config.database import engine
    await engine.dispose()


def create_application() -> FastAPI:
    """
    Factory function that creates and configures the FastAPI application.

    Using a factory function (instead of module-level instantiation)
    allows test code to create isolated app instances.

    Returns:
        Fully configured FastAPI application.
    """
    app = FastAPI(
        title="ShipFaster API",
        description=(
            "Enterprise AI Developer Automation Platform.\n\n"
            "## Authentication\n"
            "All API endpoints (except `/tenants` registration) require:\n"
            "```\nAuthorization: Bearer sf_<your_api_key>\n```\n\n"
            "## Rate Limiting\n"
            "Free plan: 100 req/min | Pro: 1000 req/min | Enterprise: Unlimited\n\n"
            "## Versioning\n"
            "This API is versioned at `/api/v1/`. Breaking changes will use a new version prefix."
        ),
        version=settings.app_version,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
        # Disable default exception handlers — we register our own
        generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}" if route.tags else route.name,
    )

    # -------------------------------------------------------------------
    # Middleware Registration (outer → inner execution order)
    # -------------------------------------------------------------------

    # 1. CORS — must be outermost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
        expose_headers=["X-Request-ID", "X-Correlation-ID"],
    )

    # 2. Request Logging — injects request_id, measures latency
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Auth — resolves tenant from Bearer token (soft — does not block)
    app.add_middleware(AuthMiddleware)

    # -------------------------------------------------------------------
    # Exception Handlers
    # -------------------------------------------------------------------
    register_exception_handlers(app)

    # -------------------------------------------------------------------
    # Route Registration
    # -------------------------------------------------------------------
    API_PREFIX = "/api/v1"

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(tenants.router, prefix=API_PREFIX)
    app.include_router(jobs.router, prefix=API_PREFIX)
    app.include_router(webhooks.router, prefix=API_PREFIX)
    app.include_router(artifacts.router, prefix=API_PREFIX)

    # Placeholder routers for Phase 3+ (will be uncommented as built):
    # app.include_router(jobs.router, prefix=API_PREFIX)
    # app.include_router(artifacts.router, prefix=API_PREFIX)
    # app.include_router(webhooks.router, prefix=API_PREFIX)
    # app.include_router(analytics.router, prefix=API_PREFIX)

    logger.info(
        "shipfaster.routes_registered",
        route_count=len(app.routes),
    )

    return app


# -------------------------------------------------------------------
# ASGI App Instance
# -------------------------------------------------------------------
# This is the object uvicorn points at:
#   uvicorn engine.api.main:app --reload --port 8000
app = create_application()
