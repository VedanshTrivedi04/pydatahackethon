"""
viaSocket HTTP Client.

Responsible for sending the outbound webhook payload to the tenant's viaSocket URL.
This client is synchronous and intended to be called from a Celery worker.
"""

import json
import urllib.request
import urllib.error
from typing import Tuple

from engine.config.settings import get_settings
from engine.utils.logging import get_logger

logger = get_logger(__name__)


def send_viasocket_webhook(url: str, payload: dict) -> Tuple[int, str]:
    """
    Send a POST request to the viaSocket webhook URL.

    Args:
        url: The viaSocket webhook URL.
        payload: The JSON-serializable dictionary to send.

    Returns:
        Tuple of (status_code: int, response_body: str)
        If a network error occurs, status_code will be 0.
    """
    settings = get_settings()
    timeout = settings.viasocket.timeout_seconds

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ShipFaster-viaSocket-Client/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            return status_code, body
    except urllib.error.HTTPError as e:
        # We got an HTTP response but it was an error code (4xx, 5xx)
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = str(e)
        return e.code, body
    except urllib.error.URLError as e:
        # Network error (DNS, connection refused, timeout)
        return 0, str(e.reason)
    except Exception as e:
        # Any other unexpected error
        return 0, str(e)
