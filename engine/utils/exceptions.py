"""
Domain Exception Hierarchy.

All business errors in ShipFaster are typed exceptions.
They are caught by FastAPI exception handlers and converted
to consistent, enterprise-formatted HTTP error responses.

NEVER raise raw Python exceptions (ValueError, KeyError, etc.)
from service or repository layers. Always raise one of these.
"""


class ShipFasterError(Exception):
    """
    Root exception for all ShipFaster domain errors.

    All custom exceptions inherit from this class, enabling
    a single catch-all handler if needed.
    """
    message: str
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


# --- 4xx Client Errors ---

class AuthenticationError(ShipFasterError):
    """
    Raised when an API key is missing, invalid, expired, or the
    associated tenant is suspended.

    HTTP 401 — Do NOT reveal WHY authentication failed (timing/info leakage).
    """
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"


class PermissionError(ShipFasterError):
    """
    Raised when an authenticated tenant attempts an action they are
    not authorized to perform.

    HTTP 403.
    """
    status_code = 403
    error_code = "PERMISSION_DENIED"


class NotFoundError(ShipFasterError):
    """
    Raised when a requested resource does not exist or has been soft-deleted.

    HTTP 404.
    """
    status_code = 404
    error_code = "NOT_FOUND"


class ValidationError(ShipFasterError):
    """
    Raised when input data fails business-level validation
    (beyond Pydantic schema validation).

    HTTP 422.
    """
    status_code = 422
    error_code = "VALIDATION_ERROR"


class ConflictError(ShipFasterError):
    """
    Raised when an operation would create a conflict with existing data
    (e.g. duplicate slug, duplicate key).

    HTTP 409.
    """
    status_code = 409
    error_code = "CONFLICT"


class RateLimitError(ShipFasterError):
    """
    Raised when a tenant exceeds their request rate limit.

    HTTP 429.
    """
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class PayloadTooLargeError(ShipFasterError):
    """
    Raised when a request payload exceeds size limits.

    HTTP 413.
    """
    status_code = 413
    error_code = "PAYLOAD_TOO_LARGE"


# --- 5xx Server Errors ---

class InternalError(ShipFasterError):
    """
    Raised when an unexpected internal error occurs.

    HTTP 500. Message is generic — details go to server logs only.
    """
    status_code = 500
    error_code = "INTERNAL_ERROR"


class ServiceUnavailableError(ShipFasterError):
    """
    Raised when a downstream service (Redis, MinIO, LLM API) is unreachable.

    HTTP 503.
    """
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"


class QueueError(ShipFasterError):
    """
    Raised when a Celery task cannot be enqueued.

    HTTP 503.
    """
    status_code = 503
    error_code = "QUEUE_ERROR"


class LLMError(ShipFasterError):
    """
    Raised when the LLM API returns an error after all retries are exhausted.

    HTTP 502.
    """
    status_code = 502
    error_code = "LLM_ERROR"


class StorageError(ShipFasterError):
    """
    Raised when MinIO/S3 operations fail.

    HTTP 502.
    """
    status_code = 502
    error_code = "STORAGE_ERROR"


class WebhookSignatureError(ShipFasterError):
    """
    Raised when a webhook payload fails HMAC signature verification.

    HTTP 401 — always reject unsigned/incorrectly-signed webhooks.
    """
    status_code = 401
    error_code = "WEBHOOK_SIGNATURE_INVALID"


class JobStateError(ShipFasterError):
    """
    Raised when a job state transition is invalid
    (e.g. trying to approve an already-completed job).

    HTTP 409.
    """
    status_code = 409
    error_code = "INVALID_JOB_STATE"
