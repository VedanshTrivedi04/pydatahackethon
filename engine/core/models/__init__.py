"""
engine/core/models package.

Imports all models so Alembic autogeneration can discover them
through the metadata attached to Base.

Import order matters — models with no FK dependencies first.
"""

from engine.core.models.base import TimestampedModel
from engine.core.models.user import User
from engine.core.models.tenant import Tenant, TenantSecret
from engine.core.models.tenant_member import TenantMember
from engine.core.models.job import Job, JobLog
from engine.core.models.artifact import Artifact
from engine.core.models.webhook import WebhookEvent
from engine.core.models.viasocket import ViaSocketDispatch
from engine.core.models.llm import LLMUsage
from engine.core.models.audit import AuditLog, APILog
from engine.core.models.notification import Notification, RetryQueue

# Pydantic ModuleResult schema for Dev 1 modules
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
            return self.__dict__

        def dict(self) -> dict:
            return self.__dict__
    HAS_PYDANTIC = False

from typing import Literal, Optional, List

class ModuleResult(BaseModel):
    status: Literal["success", "failed", "partial"]
    output: dict
    artifacts: List[str]
    error: Optional[str] = None
    
    def __init__(self, status: str, output: dict, artifacts: List[str], error: Optional[str] = None, **kwargs):
        if HAS_PYDANTIC:
            super().__init__(status=status, output=output, artifacts=artifacts, error=error, **kwargs)
        else:
            self.status = status
            self.output = output
            self.artifacts = artifacts
            self.error = error

__all__ = [
    "TimestampedModel",
    "User",
    "Tenant",
    "TenantSecret",
    "TenantMember",
    "Job",
    "JobLog",
    "Artifact",
    "WebhookEvent",
    "ViaSocketDispatch",
    "LLMUsage",
    "AuditLog",
    "APILog",
    "Notification",
    "RetryQueue",
    "ModuleResult",
]
