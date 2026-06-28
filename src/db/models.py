"""
db/models.py — SQLAlchemy ORM Models for ABSs v2.0 Multi-Tenant Proxy.

All security-critical tables are scoped to a `tenant_id` foreign key.
This ensures strict data isolation at the query level — Tenant A can never
see Tenant B's audit logs, policies, or sessions.

Table summary:
  tenants          Company/team accounts with hashed API keys.
  policies         Per-tenant security rules (blocked domains, DLP, RBAC).
  audit_logs       Immutable, append-only security event log.
  agent_sessions   Tracks individual agent job executions per tenant.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class RiskLevel(str, enum.Enum):
    """Standardized risk classification for audit events."""
    SAFE = "SAFE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionTaken(str, enum.Enum):
    """What the security engine did in response to a detected event."""
    ALLOWED = "ALLOWED"
    MONITOR = "MONITOR"
    WARNED = "WARNED"
    SANITIZED = "SANITIZED"
    BLOCKED = "BLOCKED"
    BLOCK_AND_ESCALATE = "BLOCK_AND_ESCALATE"
    EXPLAINED = "EXPLAINED"


class SessionStatus(str, enum.Enum):
    """Lifecycle status of an agent job execution."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TenantTier(str, enum.Enum):
    """Subscription tier — controls rate limits & feature access."""
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _generate_uuid() -> str:
    """Generate a URL-safe, collision-resistant UUID4 string."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Tenant(Base):
    """
    Represents a company or team that uses the ABSs proxy.

    Each tenant gets:
      - A unique API key (hashed at rest) for authentication.
      - A tier that governs rate limits and feature access.
      - Isolated policies, sessions, and audit logs.

    Security notes:
      - `api_key_hash` stores a SHA-256 hash, never the raw key.
      - `api_key_prefix` stores the first 8 chars for dashboard display
        (e.g., "sk-ab12...") so admins can identify keys without exposing them.
    """
    __tablename__ = "tenants"

    id = Column(String(32), primary_key=True, default=_generate_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    api_key_hash = Column(String(64), nullable=False, unique=True, index=True)
    api_key_prefix = Column(String(12), nullable=False)
    tier = Column(Enum(TenantTier), nullable=False, default=TenantTier.FREE)
    is_active = Column(Boolean, nullable=False, default=True)
    max_concurrent_sessions = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    policies = relationship("Policy", back_populates="tenant", cascade="all, delete-orphan")
    sessions = relationship("AgentSession", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id!r}, name={self.name!r}, tier={self.tier})>"


class Policy(Base):
    """
    Per-tenant security policy configuration.

    Each tenant has exactly one active policy at any time. Policies define:
      - Blocked domains (wildcards supported, e.g., "*.ru", "bit.ly").
      - Blocked input patterns for DLP (e.g., "password", "ssn").
      - Blocked browser actions (e.g., "open_tab", "send_keys").
      - Risk tolerance threshold (0-100).
      - Human-in-the-loop approval requirement.

    JSON columns store arrays/objects for flexibility without requiring
    a separate join table for each rule type.
    """
    __tablename__ = "policies"

    id = Column(String(32), primary_key=True, default=_generate_uuid)
    tenant_id = Column(
        String(32),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)

    # --- Rule sets (stored as JSON arrays) ---
    blocked_domains = Column(SQLiteJSON, nullable=False, default=lambda: [
        "*.ru", "*.cn", "bit.ly", "tinyurl.com", "pastebin.com",
    ])
    blocked_input_patterns = Column(SQLiteJSON, nullable=False, default=lambda: [
        "password", "ssn", "credit_card", "secret_key",
    ])
    blocked_actions = Column(SQLiteJSON, nullable=False, default=list)

    # --- Thresholds ---
    max_risk_tolerance = Column(Integer, nullable=False, default=75)
    require_human_approval = Column(Boolean, nullable=False, default=False)

    # --- Trusted domain overrides (tenant can add their own) ---
    trusted_domains = Column(SQLiteJSON, nullable=False, default=list)

    # --- Metadata ---
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="policies")

    # Constraints: only one active policy per tenant.
    __table_args__ = (
        Index("ix_policy_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Policy(id={self.id!r}, tenant={self.tenant_id!r}, active={self.is_active})>"


class AgentSession(Base):
    """
    Tracks a single agent job execution for a tenant.

    Lifecycle:
      QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED

    Each session records:
      - The user's original task prompt.
      - The target URL.
      - Execution timestamps and duration.
      - Final result summary (or error message on failure).
      - Associated audit logs via relationship.
    """
    __tablename__ = "agent_sessions"

    id = Column(String(32), primary_key=True, default=_generate_uuid)
    tenant_id = Column(
        String(32),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(SessionStatus),
        nullable=False,
        default=SessionStatus.QUEUED,
    )
    task_prompt = Column(Text, nullable=False)
    target_url = Column(String(2048), nullable=True)
    result_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Execution timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="sessions")
    audit_logs = relationship("AuditLog", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_session_tenant_status", "tenant_id", "status"),
        Index("ix_session_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentSession(id={self.id!r}, status={self.status}, tenant={self.tenant_id!r})>"


class AuditLog(Base):
    """
    Immutable, append-only security event log.

    Replaces the legacy `security_events.jsonl` file with a proper relational
    table scoped to both tenant and session. This table is the backbone of
    the SOC dashboard, XAI explanation views, and compliance reporting.

    Design notes:
      - This table is INSERT-ONLY in normal operation. The only UPDATE
        allowed is backfilling the `xai_explanation` field once the async
        Celery worker generates it.
      - `screenshot_path` stores relative paths to evidence snapshots on
        the local filesystem or object storage (S3/GCS) URI in production.
      - `risk_breakdown` stores the full JSON output of the RiskScorer
        for forensic drill-down in the dashboard.
    """
    __tablename__ = "audit_logs"

    id = Column(String(32), primary_key=True, default=_generate_uuid)
    tenant_id = Column(
        String(32),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        String(32),
        ForeignKey("agent_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Event data ---
    event_type = Column(String(64), nullable=False, index=True)
    url = Column(String(2048), nullable=True)
    details = Column(Text, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=False, default=RiskLevel.LOW)
    risk_score = Column(Integer, nullable=False, default=0)
    action_taken = Column(Enum(ActionTaken), nullable=False, default=ActionTaken.ALLOWED)

    # --- Extended data ---
    risk_breakdown = Column(SQLiteJSON, nullable=True)
    screenshot_path = Column(String(512), nullable=True)
    xai_explanation = Column(Text, nullable=True)
    xai_pending = Column(Boolean, nullable=False, default=False)

    # --- Timestamp ---
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    session = relationship("AgentSession", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_tenant_time", "tenant_id", "created_at"),
        Index("ix_audit_tenant_risk", "tenant_id", "risk_level"),
        Index("ix_audit_session", "session_id"),
        Index("ix_audit_xai_pending", "xai_pending"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id!r}, type={self.event_type!r}, "
            f"risk={self.risk_score}, tenant={self.tenant_id!r})>"
        )
