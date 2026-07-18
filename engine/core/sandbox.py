import sys
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, Tuple, Optional

def execute(code: str, additional_files: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """
    Executes the generated Python test code inside an isolated subprocess.
    Creates a temporary directory, writes the test code and any additional files,
    runs pytest (or python if pytest is not available), and cleans up.
    
    Returns:
        (passed: bool, output: str)
    """
    temp_dir = tempfile.mkdtemp(prefix="sandbox_")
    try:
        temp_path = Path(temp_dir)
        
        # Write additional files first (e.g. the source file being tested)
        if additional_files:
            for filename, content in additional_files.items():
                file_path = temp_path / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
        
        # Write test code
        test_file = temp_path / "test_generated.py"
        test_file.write_text(code, encoding="utf-8")
        
        # Check if pytest is available in current env
        # If not, fall back to running python directly
        cmd = [sys.executable, "-m", "pytest", str(test_file)]
        
        # Run process
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15, # 15 second timeout to prevent hang
            cwd=temp_dir
        )
        
        passed = (result.returncode == 0)
        output = result.stdout + "\n" + result.stderr
        
        return passed, output
        
    except subprocess.TimeoutExpired as te:
        return False, f"Execution timed out after 15 seconds.\nOutput so far:\n{te.stdout or ''}\n{te.stderr or ''}"
    except Exception as e:
        return False, f"Sandbox execution error: {str(e)}"
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
