"""
Structured Logging Utility.

Uses structlog for JSON-formatted, structured log output.
Every log entry includes: timestamp, level, logger, request_id, tenant_id, job_id.

Usage:
    from engine.utils.logging import get_logger
    logger = get_logger(__name__)
    logger.info("job.started", job_id=str(job_id), module="scaffolder")

In development: colorized human-readable output
In production:  JSON lines (structured, parseable by log aggregators)
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from engine.config.settings import get_settings

settings = get_settings()


def _add_log_level(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add the log level string to the event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def _drop_color_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Remove uvicorn's color_message key from log output."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog and stdlib logging.

    Call this ONCE at application startup in main.py lifespan.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_log_level,
        _drop_color_message_key,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_development:
        # Human-readable colored output for development
        processors: list[Any] = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # JSON output for production log aggregators
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Redirect stdlib logging through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a named structlog logger.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("event_name", key="value", another_key=123)
    """
    return structlog.get_logger(name)


def bind_request_context(
    request_id: str,
    tenant_id: str | None = None,
    job_id: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """
    Bind request-level context to the structlog context vars.

    Must be called at the start of each request (in middleware).
    These values will be automatically included in all subsequent
    log calls within the same async context.

    Args:
        request_id: Unique request ID for this HTTP request.
        tenant_id:  Resolved tenant UUID (if authenticated).
        job_id:     Job UUID if this request is job-specific.
        correlation_id: Distributed tracing correlation ID.
    """
    context: dict[str, str] = {"request_id": request_id}
    if tenant_id:
        context["tenant_id"] = tenant_id
    if job_id:
        context["job_id"] = job_id
    if correlation_id:
        context["correlation_id"] = correlation_id
    structlog.contextvars.bind_contextvars(**context)


def clear_request_context() -> None:
    """
    Clear structlog context vars after the request completes.

    Call in middleware after response is sent.
    """
    structlog.contextvars.clear_contextvars()
