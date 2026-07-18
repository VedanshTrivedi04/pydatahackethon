"""
Bearer Token Extractor.

Responsible for extracting the raw API key from the HTTP Authorization header.

Expected header format:
    Authorization: Bearer sf_<64_hex_chars>

This module only extracts — it does NOT validate or look up the key.
Validation happens in the TenantService (service layer).
"""

from dataclasses import dataclass

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass(frozen=True)
class ExtractedKey:
    """
    Result of a successful Bearer token extraction.

    Attributes:
        raw_key: The plaintext API key string (e.g. "sf_a3f1c9...").
    """
    raw_key: str


class BearerExtractor:
    """
    Extracts the Bearer API key from the Authorization header.

    This is a pure extraction utility — no DB calls, no business logic.
    It returns the raw key string or raises ValueError if the header
    is missing or malformed.

    Usage:
        extractor = BearerExtractor()
        extracted = await extractor.extract(request)
        raw_key = extracted.raw_key
    """

    def __init__(self) -> None:
        self._scheme = HTTPBearer(auto_error=False)

    async def extract(self, request: Request) -> ExtractedKey:
        """
        Extract the API key from the Authorization: Bearer header.

        Args:
            request: The incoming FastAPI Request object.

        Returns:
            ExtractedKey containing the raw API key string.

        Raises:
            ValueError: If no Authorization header is present,
                        if the scheme is not Bearer,
                        or if the credentials are empty.
        """
        credentials: HTTPAuthorizationCredentials | None = await self._scheme(request)

        if credentials is None:
            raise ValueError(
                "Missing Authorization header. "
                "Use: Authorization: Bearer sf_<your_api_key>"
            )

        if credentials.scheme.lower() != "bearer":
            raise ValueError(
                f"Invalid authentication scheme '{credentials.scheme}'. "
                "Expected 'Bearer'."
            )

        raw_key = credentials.credentials.strip()

        if not raw_key:
            raise ValueError("Authorization header contains an empty token.")

        return ExtractedKey(raw_key=raw_key)


# Singleton instance — reused across requests
bearer_extractor = BearerExtractor()
