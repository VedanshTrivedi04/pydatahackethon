"""
Event System Types.

Defines the standard system events that can be emitted and consumed
across the ShipFaster platform.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid
import datetime

EventType = Literal[
    "job.created",
    "job.status_changed",
    "job.completed",
    "job.failed",
    "tenant.created",
    "tenant.updated",
    "webhook.received",
]


class SystemEvent(BaseModel):
    """
    Standard schema for all internal system events.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = Field(description="The event type identifier")
    tenant_id: str | None = Field(default=None, description="Tenant associated with the event")
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific data payload")

