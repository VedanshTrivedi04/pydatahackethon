import logging

logger = logging.getLogger("engine.core.models")

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    logger.warning("Pydantic not found. Using custom fallback BaseModel.")
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self) -> dict:
            # Pydantic v2 compatibility
            return self.__dict__

        def dict(self) -> dict:
            # Pydantic v1 compatibility
            return self.__dict__
    HAS_PYDANTIC = False

from typing import Literal, Optional, List

class ModuleResult(BaseModel):
    status: Literal["success", "failed", "partial"]
    output: dict
    artifacts: List[str]
    error: Optional[str] = None
    
    # Custom initializer for fallback mode
    def __init__(self, status: str, output: dict, artifacts: List[str], error: Optional[str] = None, **kwargs):
        if HAS_PYDANTIC:
            super().__init__(status=status, output=output, artifacts=artifacts, error=error, **kwargs)
        else:
            self.status = status
            self.output = output
            self.artifacts = artifacts
            self.error = error
