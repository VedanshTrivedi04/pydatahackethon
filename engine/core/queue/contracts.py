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


class ModuleResult(BaseModel):
    """
    Result returned by every AI module's run() function.

    Dev 1 must return exactly this shape from every handler.
    Dev 3's Celery worker reads this and persists it to the jobs table.

    Attributes:
        status:    Terminal state of the module execution.
        output:    Module-specific output data (free-form dict).
        artifacts: List of artifact file paths/keys generated.
        error:     Error message if status is 'failed' or 'partial'.
    """

    status: Literal["success", "failed", "partial"] = Field(
        description="Terminal execution state"
    )
    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Module-specific output payload",
    )
    artifacts: list[str] = Field(
        default_factory=list,
        description="List of MinIO object keys for generated artifacts",
    )
    error: str | None = Field(
        default=None,
        description="Error description — populated when status is failed or partial",
    )
