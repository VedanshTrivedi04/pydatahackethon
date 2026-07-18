"""
Webhook Security Utilities.

Validates incoming webhook signatures using HMAC SHA-256.
GitHub signs all payloads using the Webhook Secret configured in the GitHub App.
"""

import hmac
import hashlib
from typing import Optional

from engine.config.settings import get_settings


def verify_github_signature(
    raw_body: bytes,
    signature_header: str | None,
    secret: str | None = None
) -> bool:
    """
    Verify a GitHub webhook payload signature.

    Args:
        raw_body: The raw HTTP request body bytes.
        signature_header: The 'x-hub-signature-256' header from GitHub.
        secret: Optional secret override (uses global app secret by default).

    Returns:
        True if the signature is valid or if verification is disabled in dev.
        False if the signature is invalid or missing.
    """
    settings = get_settings()
    
    # If a secret isn't provided, use the global one
    webhook_secret = secret or settings.github.webhook_secret
    
    if not webhook_secret:
        # In development, we might not have a secret configured.
        # If we have no secret, we skip validation (but log a warning ideally).
        # In production, this should fail.
        if settings.is_development:
            return True
        return False

    if not signature_header:
        return False

    # GitHub signature format: sha256=hash
    parts = signature_header.split("=")
    if len(parts) != 2 or parts[0] != "sha256":
        return False

    received_hash = parts[1]

    # Compute expected hash
    mac = hmac.new(
        key=webhook_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    )
    expected_hash = mac.hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(received_hash, expected_hash)
