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
from typing import List, Optional, Any

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


# ============================================================================
# Auth & Token Schemas
# ============================================================================

class Token(BaseModel):
    """OAuth2 JWT Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    user: Optional[Any] = None


class TokenPayload(BaseModel):
    """Payload stored in the JWT."""
    sub: Optional[str] = None
    exp: Optional[int] = None
    tenant_id: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Password change credentials."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ============================================================================
# User Schemas
# ============================================================================

class UserCreate(BaseModel):
    """Request body for creating a user within a tenant."""
    email: EmailStr = Field(..., examples=["analyst@acme.com"])
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255, examples=["Jane Doe"])
    role: str = Field(default="VIEWER", examples=["ADMIN"])

    model_config = ConfigDict(str_strip_whitespace=True)


class UserUpdate(BaseModel):
    """PATCH body for updating a user."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User info returned to the client. Never exposes the password hash."""
    id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Paginated list of users."""
    total: int
    page: int
    page_size: int
    items: List[UserResponse]


# ============================================================================
# Organization Schemas
# ============================================================================

class OrganizationCreate(BaseModel):
    """Request body for creating an organization."""
    name: str = Field(..., min_length=2, max_length=255, examples=["Acme Security"])
    slug: str = Field(..., min_length=2, max_length=255, pattern=r"^[a-z0-9-]+$", examples=["acme-security"])
    description: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class OrganizationUpdate(BaseModel):
    """PATCH body for updating an organization."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Organization info returned to the client."""
    id: str
    name: str
    slug: str
    description: Optional[str]
    owner_tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationListResponse(BaseModel):
    """Paginated list of organizations."""
    total: int
    page: int
    page_size: int
    items: List[OrganizationResponse]


# ============================================================================
# API Key Schemas
# ============================================================================

class APIKeyCreate(BaseModel):
    """Request body for creating a new API key."""
    name: str = Field(..., min_length=2, max_length=255, examples=["Production Key"])
    scopes: List[str] = Field(default_factory=lambda: ["*"], examples=[["agents:read", "agents:write"]])
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)

    model_config = ConfigDict(str_strip_whitespace=True)


class APIKeyResponse(BaseModel):
    """API key metadata returned to the client."""
    id: str
    tenant_id: str
    user_id: Optional[str]
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(APIKeyResponse):
    """Returned ONLY on key creation. Includes the raw key exactly once."""
    raw_key: str = Field(
        ...,
        description="Full API key. Store securely — it cannot be retrieved again.",
    )


class APIKeyListResponse(BaseModel):
    """Paginated list of API keys."""
    total: int
    page: int
    page_size: int
    items: List[APIKeyResponse]


# ============================================================================
# Incident Schemas
# ============================================================================

class IncidentCreate(BaseModel):
    """Request body for creating a security incident."""
    title: str = Field(..., min_length=5, max_length=500, examples=["Prompt injection detected on agent-7"])
    description: Optional[str] = None
    severity: str = Field(default="MEDIUM", examples=["HIGH"])
    session_id: Optional[str] = None
    mitre_ids: List[str] = Field(default_factory=list, examples=[["T1566", "T1048"]])
    labels: List[str] = Field(default_factory=list, examples=[["urgent", "investigated"]])

    model_config = ConfigDict(str_strip_whitespace=True)


class IncidentUpdate(BaseModel):
    """PATCH body for updating an incident."""
    title: Optional[str] = Field(default=None, min_length=5, max_length=500)
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    labels: Optional[List[str]] = None


class IncidentResponse(BaseModel):
    """Incident info returned to the client."""
    id: str
    tenant_id: str
    session_id: Optional[str]
    title: str
    description: Optional[str]
    severity: str
    status: str
    risk_score: int
    mitre_ids: List[str]
    assigned_to: Optional[str]
    resolution: Optional[str]
    labels: List[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""
    total: int
    page: int
    page_size: int
    items: List[IncidentResponse]


class IncidentCommentCreate(BaseModel):
    """Request body for adding a comment to an incident."""
    content: str = Field(..., min_length=1, max_length=4096)

    model_config = ConfigDict(str_strip_whitespace=True)


class IncidentCommentResponse(BaseModel):
    """Incident comment returned to the client."""
    id: str
    incident_id: str
    user_id: Optional[str]
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentTimelineResponse(BaseModel):
    """Incident timeline entry returned to the client."""
    id: str
    incident_id: str
    event_type: str
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Browser Session Schemas
# ============================================================================

class BrowserSessionResponse(BaseModel):
    """Browser session info returned to the client."""
    id: str
    tenant_id: str
    agent_session_id: Optional[str]
    browser_type: str
    url: Optional[str]
    status: str
    pages_visited: int
    actions_performed: int
    started_at: datetime
    ended_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class BrowserSessionListResponse(BaseModel):
    """Paginated list of browser sessions."""
    total: int
    page: int
    page_size: int
    items: List[BrowserSessionResponse]


# ============================================================================
# Security Event Schemas
# ============================================================================

class SecurityEventResponse(BaseModel):
    """Security event returned to the client."""
    id: str
    tenant_id: str
    session_id: Optional[str]
    event_type: str
    severity: str
    source: Optional[str]
    details: Optional[str]
    raw_data: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityEventListResponse(BaseModel):
    """Paginated list of security events."""
    total: int
    page: int
    page_size: int
    items: List[SecurityEventResponse]


# ============================================================================
# Tenant Settings Schemas
# ============================================================================

class TenantSettingsUpdate(BaseModel):
    """PATCH body for updating tenant settings."""
    notification_email: Optional[str] = None
    webhook_url: Optional[str] = None
    timezone: Optional[str] = None
    data_retention_days: Optional[int] = Field(default=None, ge=1, le=365)
    settings_json: Optional[dict] = None


class TenantSettingsResponse(BaseModel):
    """Tenant settings returned to the client."""
    id: str
    tenant_id: str
    notification_email: Optional[str]
    webhook_url: Optional[str]
    timezone: str
    data_retention_days: int
    settings_json: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Risk & Reputation Schemas
# ============================================================================

class RiskAssessmentRequest(BaseModel):
    """Request body for on-demand risk assessment."""
    url: Optional[str] = Field(default=None, max_length=2048)
    content: Optional[str] = None
    action: Optional[str] = None

    model_config = ConfigDict(str_strip_whitespace=True)


class RiskAssessmentResponse(BaseModel):
    """Risk assessment result."""
    risk_score: int
    risk_level: str
    breakdown: dict
    recommendations: List[str]


class ReputationCheckRequest(BaseModel):
    """Request body for URL/domain reputation check."""
    url: str = Field(..., max_length=2048)

    model_config = ConfigDict(str_strip_whitespace=True)


class ReputationCheckResponse(BaseModel):
    """Reputation check result."""
    url: str
    is_safe: bool
    risk_score: int
    categories: List[str]
    details: dict


# ============================================================================
# Analytics Schemas
# ============================================================================

class AnalyticsOverview(BaseModel):
    """Dashboard analytics overview response."""
    total_sessions: int
    total_events: int
    total_incidents: int
    active_agents: int
    risk_distribution: dict
    top_event_types: dict
    average_risk_score: float
    sessions_by_status: dict


# ============================================================================
# Job & Sandbox Schemas
# ============================================================================

class JobResponse(BaseModel):
    """Background job info."""
    id: str
    tenant_id: str
    task_name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[str]
    error: Optional[str]


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    total: int
    page: int
    page_size: int
    items: List[JobResponse]


class SandboxExecuteRequest(BaseModel):
    """Request body for sandbox execution."""
    task_prompt: str = Field(..., min_length=5, max_length=4096)
    target_url: Optional[str] = Field(default=None, max_length=2048)
    sandbox_mode: str = Field(default="isolated", examples=["isolated", "monitored"])

    model_config = ConfigDict(str_strip_whitespace=True)


class SandboxExecuteResponse(BaseModel):
    """Sandbox execution result."""
    session_id: str
    status: str
    sandbox_mode: str
    message: str


# ============================================================================
# System Health Schemas
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Detailed system health check response."""
    status: str
    service: str
    version: str
    uptime_seconds: float
    database: str
    redis: str
    timestamp: datetime