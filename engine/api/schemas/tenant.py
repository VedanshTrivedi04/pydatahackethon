"""
Tenant API Schemas — Pydantic V2.

Request and response models for the /api/v1/tenants endpoints.
These are the contract between Dev 3's API and Dev 2's frontend.

Security note:
- key_hash is NEVER included in any response schema
- The raw API key is returned ONCE on creation (CreateTenantResponse)
  and never again
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# =============================================================================
# Shared Base
# =============================================================================

class APIResponse(BaseModel):
    """
    Standard API response wrapper.

    All responses have success + data or success + error at the top level.
    """
    model_config = ConfigDict(from_attributes=True)

    success: bool = True


# =============================================================================
# API Key Schemas
# =============================================================================

class APIKeyMetadata(BaseModel):
    """
    Safe representation of an API key — no sensitive fields.

    key_hash is NEVER in any response.
    Only key_prefix (first 12 chars) is shown for identification.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    key_prefix: str = Field(description="First 12 characters of the key for identification")
    is_active: bool
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class CreateAPIKeyRequest(BaseModel):
    """Request body for generating a new API key."""

    name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional label for this key (e.g. 'CI Key', 'Production')",
    )


class CreateAPIKeyResponse(APIResponse):
    """
    Response for new API key creation.

    raw_key is included ONCE — it will never be shown again.
    The user must copy it immediately.
    """
    api_key: str = Field(
        description="The full API key — shown ONCE. Copy it now, it cannot be retrieved again."
    )
    metadata: APIKeyMetadata


# =============================================================================
# Tenant Schemas
# =============================================================================

class TenantBase(BaseModel):
    """Shared fields across create/update/read."""

    name: str = Field(
        min_length=2,
        max_length=255,
        description="Human-readable organization name",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Primary contact email",
    )
    plan: str = Field(
        default="free",
        description="Subscription tier: free | pro | enterprise",
    )


class CreateTenantRequest(TenantBase):
    """
    Request body for POST /api/v1/tenants.

    Creates a new tenant and returns their first API key.
    """
    slug: str = Field(
        min_length=4,
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9\-]{2,98}[a-z0-9]$",
        description="URL-safe unique identifier (lowercase, alphanumeric, hyphens)",
        examples=["acme-corp", "my-startup"],
    )
    initial_key_name: str = Field(
        default="Default Key",
        max_length=100,
        description="Label for the first API key",
    )


class UpdateTenantRequest(BaseModel):
    """
    Request body for PATCH /api/v1/tenants/{tenant_id}.

    All fields optional — only provided fields are updated.
    """
    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = Field(default=None)
    viasocket_webhook_url: str | None = Field(
        default=None,
        max_length=2000,
        description="viaSocket outbound webhook URL for this tenant",
    )
    plan: str | None = Field(
        default=None,
        description="Subscription tier: free | pro | enterprise",
    )

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: str | None) -> str | None:
        if v is not None and v not in ("free", "pro", "enterprise"):
            raise ValueError("plan must be one of: free, pro, enterprise")
        return v


class TenantSchema(BaseModel):
    """
    Full tenant representation (response model).

    Note: github_webhook_secret is NOT included — that stays server-side.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    email: str | None
    plan: str
    is_active: bool
    github_app_installation_id: str | None
    viasocket_webhook_url: str | None
    created_at: datetime
    updated_at: datetime


class TenantDetailSchema(TenantSchema):
    """Extended tenant view with API key list (for tenant management pages)."""
    api_keys: list[APIKeyMetadata] = Field(default_factory=list)


class TenantListResponse(APIResponse):
    """Response for GET /api/v1/tenants (admin endpoint)."""
    tenants: list[TenantSchema]
    total: int
    limit: int
    offset: int


class TenantResponse(APIResponse):
    """Response for single tenant operations."""
    tenant: TenantSchema


class CreateTenantResponse(APIResponse):
    """
    Response for POST /api/v1/tenants.

    Includes the raw API key — shown ONLY at creation.
    """
    tenant: TenantSchema
    api_key: str = Field(
        description="Your API key. Store it safely — this is the only time it will be shown."
    )
    key_metadata: APIKeyMetadata
