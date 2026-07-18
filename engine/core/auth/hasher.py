"""
API Key Hashing Utilities.

Security contract:
- API keys are generated as cryptographically random strings with a prefix
- Only the SHA-256 hash is ever stored in the database
- The raw key is shown exactly ONCE to the user at creation time
- Verification is constant-time to prevent timing attacks

Key format: sf_{32_random_bytes_hex}
Example:    sf_a3f1c9b7e2d84f06a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4
"""

import hashlib
import hmac
import os
import secrets


# All ShipFaster API keys start with this prefix — immediately identifiable
API_KEY_PREFIX = "sf_"
# Length of the random part (bytes → 64 hex chars)
API_KEY_RANDOM_BYTES = 32


def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns a tuple of:
        (raw_key, key_hash, key_prefix)

    - raw_key:    The full plaintext key — show once, never store
    - key_hash:   SHA-256 hex digest — store this in tenant_secrets.key_hash
    - key_prefix: First 12 chars of raw_key — safe to display for identification

    Example:
        raw_key    = "sf_a3f1c9b7e2d84f06..."
        key_hash   = "9a4c8e2f1b7d3..."  (SHA-256)
        key_prefix = "sf_a3f1c9b7"
    """
    random_part = secrets.token_hex(API_KEY_RANDOM_BYTES)
    raw_key = f"{API_KEY_PREFIX}{random_part}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """
    Compute SHA-256 hash of an API key.

    Args:
        raw_key: The plaintext API key string.

    Returns:
        Lowercase hex digest string (64 characters).
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """
    Constant-time comparison of a candidate key against the stored hash.

    Uses hmac.compare_digest to prevent timing attacks — never use == directly.

    Args:
        raw_key:     The key submitted in the Authorization header.
        stored_hash: The SHA-256 hash stored in tenant_secrets.key_hash.

    Returns:
        True if the key is valid, False otherwise.
    """
    candidate_hash = hash_api_key(raw_key)
    # hmac.compare_digest is constant-time — prevents timing side-channels
    return hmac.compare_digest(candidate_hash, stored_hash)


def is_valid_key_format(raw_key: str) -> bool:
    """
    Fast format check before hitting the database.

    Rejects obviously malformed keys before any DB lookup,
    reducing load from invalid requests.

    Args:
        raw_key: The candidate API key string.

    Returns:
        True if the key has the expected format.
    """
    if not isinstance(raw_key, str):
        return False
    if not raw_key.startswith(API_KEY_PREFIX):
        return False
    remainder = raw_key[len(API_KEY_PREFIX):]
    # Must be exactly 64 hex characters
    if len(remainder) != API_KEY_RANDOM_BYTES * 2:
        return False
    # Must be valid hexadecimal
    try:
        int(remainder, 16)
    except ValueError:
        return False
    return True
