"""
Module Result — Domain Contract (Dev 1 → Dev 3).

Defines the exact shape of what every AI module must return.
Dev 1 owns the implementation of run() — Dev 3 owns the contract.

This is the ONLY interface between the module layer (Dev 1)
and the Celery worker layer (Dev 3). Never break this contract
without a team sync.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ArtifactData(BaseModel):
    """
    Data representing a generated artifact to be uploaded to MinIO.
    """
    file_name: str = Field(description="Name of the file (e.g., test_auth.py)")
    content: bytes | str = Field(description="Raw file contents")
    content_type: str = Field(default="application/octet-stream", description="MIME type")
    metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata")

class ModuleResult(BaseModel):
    """
    Result returned by every AI module's run() function.

    Dev 1 must return exactly this shape from every handler.
    Dev 3's Celery worker reads this, uploads artifacts to MinIO,
    and persists it to the jobs table.

    Attributes:
        status:    Terminal state of the module execution.
        output:    Module-specific output data (free-form dict).
        artifacts: List of ArtifactData objects containing the raw generated files.
        error:     Error message if status is 'failed' or 'partial'.
    """

    status: Literal["success", "failed", "partial"] = Field(
        description="Terminal execution state"
    )
    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Module-specific output payload",
    )
    artifacts: list[ArtifactData] = Field(
        default_factory=list,
        description="List of raw artifacts to upload to MinIO and persist",
    )
    error: str | None = Field(
        default=None,
        description="Error description — populated when status is failed or partial",
    )
