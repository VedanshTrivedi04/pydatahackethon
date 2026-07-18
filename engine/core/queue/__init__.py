"""
Queue package exports.
"""

from engine.core.queue.celery_app import (
    celery_app,
    MODULE_QUEUE_MAP,
    QUEUE_DEFAULT,
    QUEUE_DLQ,
    QUEUE_HIGH_PRIORITY,
    QUEUE_LOW_PRIORITY,
)
from engine.core.queue.contracts import ModuleResult

__all__ = [
    "celery_app",
    "MODULE_QUEUE_MAP",
    "QUEUE_DEFAULT",
    "QUEUE_DLQ",
    "QUEUE_HIGH_PRIORITY",
    "QUEUE_LOW_PRIORITY",
    "ModuleResult",
]
