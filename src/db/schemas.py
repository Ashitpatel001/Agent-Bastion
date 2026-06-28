"""
db/schemas.py — Pydantic V2 Schemas for ABSs v2.0.

These schemas serve as the data contracts between:
  - The FastAPI REST endpoints (request/response validation).
  - The CRUD layer (input validation before DB writes).
  - The Celery workers (serialized task payloads).

Naming conventions:
  - *Create  — used for POST request bodies.
  - *Update  — used for PATCH/PUT request bodies (all fields optional).
  - *Response — returned to the client (excludes sensitive fields like hashes).
  - *InDB     — internal representation including all DB columns.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================================================
# Tenant Schemas
# ============================================================================

class TenantCreate(BaseModel):
    """Request body for registering a new tenant."""
    name: str = Field(..., min_length=2, max_length=255, examples=["Acme Corp"])
    email: EmailStr = Field(..., examples=["admin@acme.com"])

    model_config = ConfigDict(str_strip_whitespace=True)


class TenantResponse(BaseModel):
    """Tenant info returned to the client. Never exposes the API key hash."""
    id: str
    name: str
    email: str
    tier: str
    is_active: bool
    api_key_prefix: str
    max_concurrent_sessions: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TenantWithApiKey(TenantResponse):
    """
    Returned ONLY on tenant creation. Includes the raw API key exactly once.
    After this response, the raw key is never stored or retrievable.
    """
    api_key: str = Field(
        ...,
        description="Full API key. Store this securely — it cannot be retrieved again.",
    )


# ============================================================================
# Policy Schemas
# ============================================================================

class PolicyCreate(BaseModel):
    """Request body for creating a new policy for the authenticated tenant."""
    blocked_domains: List[str] = Field(
        default_factory=lambda: ["*.ru", "*.cn", "bit.ly", "tinyurl.com", "pastebin.com"],
        examples=[["*.ru", "*.cn", "bit.ly"]],
    )
    blocked_input_patterns: List[str] = Field(
        default_factory=lambda: ["password", "ssn", "credit_card", "secret_key"],
        examples=[["password", "ssn"]],
    )
    blocked_actions: List[str] = Field(
        default_factory=list,
        examples=[["open_tab", "send_keys"]],
    )
    trusted_domains: List[str] = Field(
        default_factory=list,
        description="Additional domains the tenant considers safe beyond the global whitelist.",
        examples=[["internal.acme.com", "staging.acme.com"]],
    )
    max_risk_tolerance: int = Field(
        default=75,
        ge=0,
        le=100,
        description="Actions with risk scores above this threshold are automatically blocked.",
    )
    require_human_approval: bool = Field(
        default=False,
        description="If true, high-risk actions require explicit human approval (future feature).",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class PolicyUpdate(BaseModel):
    """
    PATCH body for updating an existing policy.
    Only provided fields are updated; the rest remain unchanged.
    """
    blocked_domains: Optional[List[str]] = None
    blocked_input_patterns: Optional[List[str]] = None
    blocked_actions: Optional[List[str]] = None
    trusted_domains: Optional[List[str]] = None
    max_risk_tolerance: Optional[int] = Field(default=None, ge=0, le=100)
    require_human_approval: Optional[bool] = None


class PolicyResponse(BaseModel):
    """Policy configuration returned to the client."""
    id: str
    tenant_id: str
    is_active: bool
    blocked_domains: List[str]
    blocked_input_patterns: List[str]
    blocked_actions: List[str]
    trusted_domains: List[str]
    max_risk_tolerance: int
    require_human_approval: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Agent Session Schemas
# ============================================================================

class AgentSessionCreate(BaseModel):
    """Request body for submitting a new agent job."""
    task_prompt: str = Field(
        ...,
        min_length=5,
        max_length=4096,
        examples=["Go to amazon.com, search for laptops, and summarize the top 3 results."],
    )
    target_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        examples=["https://amazon.com"],
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class AgentSessionResponse(BaseModel):
    """Agent session info returned to the client."""
    id: str
    tenant_id: str
    status: str
    task_prompt: str
    target_url: Optional[str]
    result_summary: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Audit Log Schemas
# ============================================================================

class AuditLogCreate(BaseModel):
    """
    Internal schema for inserting a new audit log entry.
    Not exposed directly via the API — the security engine uses this.
    """
    tenant_id: str
    session_id: Optional[str] = None
    event_type: str
    url: Optional[str] = None
    details: Optional[str] = None
    risk_level: str = "LOW"
    risk_score: int = Field(default=0, ge=0, le=100)
    action_taken: str = "ALLOWED"
    risk_breakdown: Optional[dict] = None
    screenshot_path: Optional[str] = None
    xai_explanation: Optional[str] = None
    xai_pending: bool = False


class AuditLogResponse(BaseModel):
    """Audit log entry returned to the client via the dashboard API."""
    id: str
    tenant_id: str
    session_id: Optional[str]
    event_type: str
    url: Optional[str]
    details: Optional[str]
    risk_level: str
    risk_score: int
    action_taken: str
    risk_breakdown: Optional[dict]
    screenshot_path: Optional[str]
    xai_explanation: Optional[str]
    xai_pending: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Paginated list of audit logs."""
    total: int
    page: int
    page_size: int
    items: List[AuditLogResponse]


# ============================================================================
# Generic API Response Wrappers
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation completed successfully."


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
