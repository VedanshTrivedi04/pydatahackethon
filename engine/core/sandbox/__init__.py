"""Sandbox package exports."""

import sys
import subprocess
import tempfile
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger("engine.core.sandbox")

from engine.core.sandbox.client import SandboxClient, SandboxExecutionResult

def execute(code: str, additional_files: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """
    Executes Python test code. Attempts to use SandboxClient if configured and reachable.
    Otherwise, falls back to running the code locally in a subprocess.
    """
    # 1. Attempt to run using real SandboxClient
    try:
        from engine.config.settings import get_settings
        settings = get_settings().sandbox
        # If endpoint_url is dummy/default or empty, skip directly to fallback
        if settings.endpoint_url and "dummy" not in settings.endpoint_url and "example.com" not in settings.endpoint_url:
            client = SandboxClient()
            # The client expects code: str
            res = client.execute_code(code)
            passed = (res.exit_code == 0)
            output = res.stdout + "\n" + res.stderr
            return passed, output
    except Exception as e:
        logger.warning(
            f"Could not run in remote sandbox: {str(e)}. Falling back to local subprocess sandbox."
        )
        
    # 2. Local fallback
    temp_dir = tempfile.mkdtemp(prefix="sandbox_")
    try:
        temp_path = Path(temp_dir)
        
        # Write additional files (e.g. source file under test)
        if additional_files:
            for filename, content in additional_files.items():
                file_path = temp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
        
        # Write test code
        test_file = temp_path / "test_generated.py"
        test_file.write_text(code, encoding="utf-8")
        
        cmd = [sys.executable, "-m", "pytest", str(test_file)]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=temp_dir
        )
        
        passed = (result.returncode == 0)
        output = result.stdout + "\n" + result.stderr
        return passed, output
        
    except subprocess.TimeoutExpired as te:
        return False, f"Execution timed out after 15 seconds.\nOutput so far:\n{te.stdout or ''}\n{te.stderr or ''}"
    except Exception as err:
        return False, f"Sandbox local execution error: {str(err)}"
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

__all__ = ["SandboxClient", "SandboxExecutionResult", "execute"]
