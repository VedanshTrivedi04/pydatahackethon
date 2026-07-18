"""
Sandbox Executor Client.

API client to trigger an isolated Docker container or Firecracker microVM.
Used by AI modules (e.g. test_generator) to safely execute generated code
and verify it compiles/runs without destroying the host.
"""

import json
import urllib.request
import urllib.error
from typing import Any

from pydantic import BaseModel, Field

from engine.config.settings import get_settings
from engine.utils.exceptions import BusinessValidationError
from engine.utils.logging import get_logger

logger = get_logger(__name__)


class SandboxExecutionResult(BaseModel):
    """Result of running code inside the sandbox."""
    
    stdout: str = Field(default="")
    stderr: str = Field(default="")
    exit_code: int = Field(default=0)
    duration_ms: int = Field(default=0)
    timed_out: bool = Field(default=False)


class SandboxClient:
    """Client for interacting with the external sandbox execution API."""

    def __init__(self) -> None:
        self.settings = get_settings().sandbox

    def execute_code(
        self,
        code: str,
        language: str = "python",
        dependencies: list[str] | None = None,
        timeout_seconds: int | None = None
    ) -> SandboxExecutionResult:
        """
        Execute arbitrary code safely inside the sandbox.
        
        Args:
            code: The source code string to run.
            language: The programming language (e.g., python, bash).
            dependencies: Optional list of packages to install first (e.g. pip packages).
            timeout_seconds: Max execution time before killing the sandbox.
            
        Returns:
            SandboxExecutionResult with stdout, stderr, and exit code.
        """
        timeout = timeout_seconds or self.settings.timeout_seconds
        
        payload = {
            "code": code,
            "language": language,
            "dependencies": dependencies or [],
            "timeout_seconds": timeout,
            "max_memory_mb": self.settings.max_memory_mb
        }
        
        data = json.dumps(payload).encode("utf-8")
        url = f"{self.settings.endpoint_url}/execute"
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
                "User-Agent": "ShipFaster-Sandbox-Client/1.0"
            },
            method="POST",
        )

        try:
            # We set the HTTP timeout slightly higher than the execution timeout
            with urllib.request.urlopen(req, timeout=timeout + 5) as response:
                body = response.read().decode("utf-8")
                result_data = json.loads(body)
                
                logger.info(
                    "sandbox.execution_completed",
                    language=language,
                    exit_code=result_data.get("exit_code")
                )
                
                return SandboxExecutionResult(
                    stdout=result_data.get("stdout", ""),
                    stderr=result_data.get("stderr", ""),
                    exit_code=result_data.get("exit_code", -1),
                    duration_ms=result_data.get("duration_ms", 0),
                    timed_out=result_data.get("timed_out", False)
                )
                
        except urllib.error.HTTPError as e:
            logger.error("sandbox.http_error", status_code=e.code, reason=e.reason)
            raise BusinessValidationError(f"Sandbox execution failed: {e.reason}")
        except urllib.error.URLError as e:
            logger.error("sandbox.network_error", reason=str(e.reason))
            raise BusinessValidationError(f"Could not connect to sandbox: {str(e.reason)}")
        except Exception as e:
            logger.error("sandbox.unexpected_error", error=str(e))
            raise BusinessValidationError(f"Unexpected sandbox error: {str(e)}")
