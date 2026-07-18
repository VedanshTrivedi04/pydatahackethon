"""
viaSocket Contracts.

Defines the exact schema of the outbound webhook payload that we POST
to the tenant's viaSocket URL. This is the API contract we promise to viaSocket.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import uuid


class ViaSocketPayload(BaseModel):
    """
    The outbound payload sent to a tenant's viaSocket webhook URL.

    Contract:
        {
            "event": "job_completed" | "job_approved",
            "tenant_id": "uuid",
            "job_id": "uuid",
            "module": "notebook_to_blog",
            "data": { ... module specific output ... }
        }
    """
    model_config = ConfigDict(from_attributes=True)

    event: str = Field(description="The event that triggered the webhook (e.g., job_completed, job_approved)")
    tenant_id: uuid.UUID = Field(description="ID of the tenant that owns the job")
    job_id: uuid.UUID = Field(description="ID of the job that completed")
    module: str = Field(description="Name of the module that ran (e.g., notebook_to_blog)")
    data: dict[str, Any] = Field(description="The artifact or output data from the job")
