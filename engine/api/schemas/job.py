"""
Job API Schemas — Pydantic V2.

These are the API contracts between Dev 3's backend and Dev 2's frontend.
Dev 2 should generate a typed TypeScript client from the OpenAPI schema
at GET /api/v1/openapi.json.

Every response uses the standard APIResponse wrapper:
{
    "success": true,
    "data": { ... }
}
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from engine.api.schemas.tenant import APIResponse


# =============================================================================
# Job Log Schema
# =============================================================================

class JobLogSchema(BaseModel):
    """Single job execution log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event: str
    message: str
    level: str
    context: dict[str, Any] | None = None
    created_at: datetime


# =============================================================================
# Artifact Schema (lightweight — full details in artifact routes)
# =============================================================================

class ArtifactSummary(BaseModel):
    """Minimal artifact info included in job responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    content_type: str
    size_bytes: int | None = None
    version: int


# =============================================================================
# Job Schemas
# =============================================================================

class JobSchema(BaseModel):
    """
    Full job representation returned by the API.

    This is the primary contract for Dev 2's job history and detail views.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    module: Literal[
        "scaffolder",
        "test_generator",
        "docs_generator",
        "changelog_generator",
        "notebook_to_blog",
    ]
    trigger: str
    status: Literal[
        "queued",
        "running",
        "success",
        "failed",
        "partial",
        "cancelled",
        "approval_pending",
        "approved",
        "rejected",
    ]
    priority: int
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    celery_task_id: str | None = None
    retry_count: int
    requires_approval: bool
    approved_by: str | None = None
    approval_note: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class JobDetailSchema(JobSchema):
    """Extended job view with logs and artifacts (for job detail page)."""

    logs: list[JobLogSchema] = Field(default_factory=list)
    artifacts: list[ArtifactSummary] = Field(default_factory=list)


# =============================================================================
# Request Schemas
# =============================================================================

class SubmitJobRequest(BaseModel):
    """
    Request body for POST /api/v1/jobs.

    This is the primary way to submit a job via API.
    Webhook and CLI triggers create jobs internally without this schema.
    """

    module: Literal[
        "scaffolder",
        "test_generator",
        "docs_generator",
        "changelog_generator",
        "notebook_to_blog",
    ] = Field(description="Which AI module to execute")

    payload: dict[str, Any] = Field(
        description=(
            "Module-specific input payload. "
            "Schema varies per module — see module documentation. "
            "Examples:\n"
            "- scaffolder: {\"stack\": \"fastapi\", \"name\": \"my-service\"}\n"
            "- test_generator: {\"repo_url\": \"...\", \"file_path\": \"...\"}\n"
            "- changelog_generator: {\"repo_url\": \"...\", \"commit_range\": \"v1.0..v1.1\"}"
        )
    )

    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Queue priority: 1=highest urgency, 10=lowest. Default=5.",
    )


class ApproveJobRequest(BaseModel):
    """Request body for POST /api/v1/jobs/{job_id}/approve."""

    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional approval note (shown in audit log)",
    )


class RejectJobRequest(BaseModel):
    """Request body for POST /api/v1/jobs/{job_id}/reject."""

    note: str | None = Field(
        default=None,
        max_length=1000,
        description="Reason for rejection (stored in audit log)",
    )


# =============================================================================
# Response Schemas
# =============================================================================

class JobResponse(APIResponse):
    """Response for single job operations."""
    job: JobSchema


class JobDetailResponse(APIResponse):
    """Response for job detail view (includes logs + artifacts)."""
    job: JobDetailSchema


class JobListResponse(APIResponse):
    """Paginated job list response."""
    jobs: list[JobSchema]
    total: int
    limit: int
    offset: int
    filters: dict[str, str | None] = Field(default_factory=dict)


class JobStatusCountsResponse(APIResponse):
    """
    Job status summary for the analytics dashboard.

    Used by Dev 2's dashboard widget.
    """
    counts: dict[str, int]
    total: int
