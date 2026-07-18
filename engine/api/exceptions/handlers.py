"""
Global Exception Handlers for FastAPI.

Converts domain exceptions and unexpected errors into
consistent, enterprise-formatted HTTP error responses.

Response format (all errors):
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Tenant 'xyz' not found.",
        "request_id": "uuid-...",
        "timestamp": "2025-01-01T00:00:00Z"
    }
}

Rules:
- NEVER expose internal tracebacks in responses
- NEVER expose raw SQLAlchemy errors
- NEVER expose file paths or internal state
- Always include request_id for support correlation
"""

import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from engine.utils.exceptions import (
    AuthenticationError,
    ConflictError,
    InternalError,
    JobStateError,
    LLMError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionError,
    QueueError,
    RateLimitError,
    ServiceUnavailableError,
    ShipFasterError,
    StorageError,
    ValidationError,
    WebhookSignatureError,
)
from engine.utils.logging import get_logger

logger = get_logger(__name__)


def _error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
) -> JSONResponse:
    """
    Build a standardized error JSON response.

    Args:
        request:     Current HTTP request (for request_id extraction).
        status_code: HTTP status code.
        error_code:  Machine-readable error code string.
        message:     Human-readable error description.

    Returns:
        JSONResponse with standardized error body.
    """
    request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Call this during app creation — before any requests are processed.

    Args:
        app: The FastAPI application instance.
    """

    # --- Domain Exceptions (ShipFasterError subclasses) ---

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return _error_response(request, 401, exc.error_code, exc.message)

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
        return _error_response(request, 403, exc.error_code, exc.message)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(request, 404, exc.error_code, exc.message)

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return _error_response(request, 409, exc.error_code, exc.message)

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(request, 422, exc.error_code, exc.message)

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError) -> JSONResponse:
        return _error_response(request, 429, exc.error_code, exc.message)

    @app.exception_handler(PayloadTooLargeError)
    async def payload_too_large_handler(request: Request, exc: PayloadTooLargeError) -> JSONResponse:
        return _error_response(request, 413, exc.error_code, exc.message)

    @app.exception_handler(JobStateError)
    async def job_state_handler(request: Request, exc: JobStateError) -> JSONResponse:
        return _error_response(request, 409, exc.error_code, exc.message)

    @app.exception_handler(WebhookSignatureError)
    async def webhook_sig_handler(request: Request, exc: WebhookSignatureError) -> JSONResponse:
        return _error_response(request, 401, exc.error_code, exc.message)

    @app.exception_handler(LLMError)
    async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
        return _error_response(request, 502, exc.error_code, exc.message)

    @app.exception_handler(StorageError)
    async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
        return _error_response(request, 502, exc.error_code, exc.message)

    @app.exception_handler(QueueError)
    async def queue_error_handler(request: Request, exc: QueueError) -> JSONResponse:
        return _error_response(request, 503, exc.error_code, exc.message)

    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
        return _error_response(request, 503, exc.error_code, exc.message)

    @app.exception_handler(ShipFasterError)
    async def generic_domain_error_handler(request: Request, exc: ShipFasterError) -> JSONResponse:
        """Catch-all for any ShipFasterError subclass not explicitly handled above."""
        return _error_response(request, exc.status_code, exc.error_code, exc.message)

    # --- Pydantic Validation Errors ---

    @app.exception_handler(RequestValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Convert Pydantic V2 validation errors to enterprise format.

        Includes field-level error details since these are client errors
        (the client needs to know what to fix).
        """
        request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": errors,
                },
            },
        )

    # --- Catch-All for Unexpected Exceptions ---

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch any unhandled exception and return a safe 500 response.

        The full traceback is logged server-side but NEVER exposed to the client.
        """
        request_id = getattr(getattr(request, "state", None), "request_id", "unknown")
        logger.error(
            "unhandled_exception",
            exc_type=type(exc).__name__,
            traceback=traceback.format_exc(),
            path=request.url.path,
            method=request.method,
        )
        return _error_response(
            request,
            500,
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please retry. If the issue persists, "
            f"contact support with request_id: {request_id}",
        )
