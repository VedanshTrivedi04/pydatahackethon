"""
Webhook API Schemas — Pydantic V2.

Defines schemas for incoming webhook payloads. We don't strictly model
the entire GitHub payload (it's massive and changes often). Instead, we
extract the key fields we need (installation ID, action, repo name) and
keep the rest as a dynamic dictionary (`payload`).
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class GitHubInstallation(BaseModel):
    """GitHub App Installation info."""
    model_config = ConfigDict(extra="ignore")
    id: int


class GitHubRepository(BaseModel):
    """GitHub Repository info."""
    model_config = ConfigDict(extra="ignore")
    full_name: str
    html_url: str


class GitHubWebhookPayload(BaseModel):
    """
    Minimal schema for a GitHub webhook payload.
    We capture installation ID to route to the correct tenant.
    """
    model_config = ConfigDict(extra="allow")

    action: str | None = None
    installation: GitHubInstallation | None = None
    repository: GitHubRepository | None = None


class WebhookResponse(BaseModel):
    """Response returned to the webhook provider (e.g. GitHub)."""
    success: bool
    message: str
    job_id: str | None = None
    event_id: str | None = None
