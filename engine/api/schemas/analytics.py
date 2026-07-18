"""
Analytics API Schemas — Pydantic V2.

Defines schemas for dashboard and reporting endpoints.
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class JobSummaryResponse(BaseModel):
    """Job status counts summary for a tenant."""
    model_config = ConfigDict(from_attributes=True)

    total: int = Field(default=0, description="Total number of jobs")
    queued: int = Field(default=0, description="Jobs waiting in queue")
    running: int = Field(default=0, description="Jobs currently executing")
    success: int = Field(default=0, description="Jobs successfully completed")
    failed: int = Field(default=0, description="Jobs that failed (terminal)")
    approval_pending: int = Field(default=0, description="Jobs waiting for human approval")
    partial: int = Field(default=0, description="Jobs that completed with partial success")
    cancelled: int = Field(default=0, description="Jobs cancelled by the user")


class LLMUsageSummaryResponse(BaseModel):
    """Aggregated LLM usage and cost summary for a tenant."""
    model_config = ConfigDict(from_attributes=True)

    total_requests: int = Field(default=0, description="Total number of LLM API calls")
    total_input_tokens: int = Field(default=0, description="Total prompt tokens consumed")
    total_output_tokens: int = Field(default=0, description="Total generation tokens consumed")
    total_tokens: int = Field(default=0, description="Total tokens (input + output)")
    total_cost_usd: Decimal = Field(default=Decimal("0.0000"), description="Total estimated cost in USD")
