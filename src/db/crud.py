"""
db/crud.py — CRUD Operations for ABSs v2.0 Multi-Tenant Proxy.

Security-critical design:
  - Every query that touches tenant-scoped data MUST include a
    `.where(Model.tenant_id == tenant_id)` filter. There is no global
    "get all tenants' data" function — this is by design to prevent
    accidental cross-tenant data leakage.
  - API keys are hashed with SHA-256 before storage. The raw key is
    returned exactly once on creation and never stored.
  - Audit logs are append-only in normal operation. The only permitted
    UPDATE is backfilling the `xai_explanation` field.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Any, Dict

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    ActionTaken,
    AgentSession,
    AuditLog,
    Policy,
    RiskLevel,
    SessionStatus,
    Tenant,
    TenantTier,
    RefreshToken,
    APIKeyRecord,
)
from db.schemas import (
    AuditLogCreate,
    PolicyCreate,
    PolicyUpdate,
)

logger = logging.getLogger("db.crud")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
API_KEY_PREFIX = "abs_"
API_KEY_BYTES = 32  # 256-bit entropy


def _hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key for storage."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a cryptographically secure API key.

    Returns:
        (raw_key, key_hash, key_prefix)
    """
    token = secrets.token_urlsafe(API_KEY_BYTES)
    raw_key = f"{API_KEY_PREFIX}{token}"
    key_hash = _hash_api_key(raw_key)
    key_prefix = raw_key[:12]  # e.g., "abs_Xk9m2bQ1"
    return raw_key, key_hash, key_prefix


# ============================================================================
# Tenant CRUD
# ============================================================================

async def create_tenant(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    tier: TenantTier = TenantTier.FREE,
) -> Tuple[Tenant, str]:
    """
    Register a new tenant and generate their API key.

    Returns:
        (tenant_object, raw_api_key)
        The raw API key is returned ONCE. It is never stored or retrievable.
    """
    raw_key, key_hash, key_prefix = _generate_api_key()

    tenant = Tenant(
        name=name,
        email=email,
        api_key_hash=key_hash,
        api_key_prefix=key_prefix,
        tier=tier,
    )
    db.add(tenant)
    await db.flush()  # Populate `tenant.id` without committing.

    # Auto-create a default policy for the new tenant.
    default_policy = Policy(tenant_id=tenant.id)
    db.add(default_policy)
    await db.flush()

    logger.info("Created tenant %r (id=%s, tier=%s)", name, tenant.id, tier)
    return tenant, raw_key


async def get_tenant_by_api_key(
    db: AsyncSession, raw_api_key: str
) -> Optional[Tenant]:
    """
    Look up a tenant by their raw API key.
    Checks both legacy Tenant.api_key_hash AND granular APIKeyRecord table.
    """
    key_hash = _hash_api_key(raw_api_key)
    result = await db.execute(
        select(Tenant).where(
            Tenant.api_key_hash == key_hash,
            Tenant.is_active == True,  # noqa: E712
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant

    # Check APIKeyRecord table (Task 2.4)
    res = await db.execute(
        select(APIKeyRecord).where(
            APIKeyRecord.key_hash == key_hash,
            APIKeyRecord.is_active == True,  # noqa: E712
        )
    )
    record = res.scalar_one_or_none()
    if record and record.tenant_id:
        # Check expiration if set
        if record.expires_at:
            exp_time = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
            if exp_time < datetime.now(timezone.utc):
                return None
        return await get_tenant_by_id(db, record.tenant_id)

    return None


async def get_tenant_by_id(
    db: AsyncSession, tenant_id: str
) -> Optional[Tenant]:
    """Retrieve a tenant by primary key."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Refresh Token Operations (Phase 2 Task 2.3)
# ---------------------------------------------------------------------------
def _hash_token(raw_token: str) -> str:
    """Hash a raw token with SHA-256 for secure storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def create_refresh_token_record(
    db: AsyncSession,
    token_id: str,
    user_id: str,
    family_id: str,
    raw_refresh_token: str,
    expires_at: datetime
) -> RefreshToken:
    """Create a new RefreshToken entry in the database."""
    token_hash = _hash_token(raw_refresh_token)
    db_token = RefreshToken(
        id=token_id,
        user_id=user_id,
        family_id=family_id,
        token_hash=token_hash,
        is_revoked=False,
        expires_at=expires_at
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token


async def get_refresh_token_by_id(
    db: AsyncSession, token_id: str
) -> Optional[RefreshToken]:
    """Retrieve a RefreshToken row by token ID / JTI."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.id == token_id)
    )
    return result.scalar_one_or_none()


async def revoke_refresh_token_family(
    db: AsyncSession, family_id: str
) -> int:
    """Revoke all tokens in a family upon detecting reuse/replay attacks."""
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id)
        .values(is_revoked=True)
    )
    await db.commit()
    return result.rowcount or 0


async def revoke_user_refresh_tokens(
    db: AsyncSession, user_id: str
) -> int:
    """Revoke all active refresh tokens for a user (e.g. on logout or password change)."""
    result = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False  # noqa: E712
        )
        .values(is_revoked=True)
    )
    await db.commit()
    return result.rowcount or 0


async def get_tenant_by_email(
    db: AsyncSession, email: str
) -> Optional[Tenant]:
    """Retrieve a tenant by email address."""
    result = await db.execute(
        select(Tenant).where(Tenant.email == email)
    )
    return result.scalar_one_or_none()


async def deactivate_tenant(
    db: AsyncSession, tenant_id: str
) -> bool:
    """Soft-delete a tenant by marking them inactive."""
    result = await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(is_active=False, updated_at=datetime.now(timezone.utc))
    )
    return result.rowcount > 0


async def regenerate_api_key(
    db: AsyncSession, tenant_id: str
) -> Optional[str]:
    """
    Rotate a tenant's API key. Returns the new raw key.
    The old key becomes invalid immediately.
    """
    raw_key, key_hash, key_prefix = _generate_api_key()
    result = await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id, Tenant.is_active == True)  # noqa: E712
        .values(
            api_key_hash=key_hash,
            api_key_prefix=key_prefix,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount > 0:
        logger.info("Regenerated API key for tenant %s", tenant_id)
        return raw_key
    return None


# ============================================================================
# Policy CRUD
# ============================================================================

async def get_active_policy(
    db: AsyncSession, tenant_id: str
) -> Optional[Policy]:
    """
    Retrieve the currently active policy for a tenant.
    Each tenant has at most one active policy.
    """
    result = await db.execute(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def create_policy(
    db: AsyncSession,
    tenant_id: str,
    data: PolicyCreate,
) -> Policy:
    """
    Create a new policy for a tenant, deactivating any existing active policy.
    This ensures policy versioning — old policies are kept for audit trails.
    """
    # Deactivate current active policy.
    await db.execute(
        update(Policy)
        .where(Policy.tenant_id == tenant_id, Policy.is_active == True)  # noqa: E712
        .values(is_active=False, updated_at=datetime.now(timezone.utc))
    )

    policy = Policy(
        tenant_id=tenant_id,
        blocked_domains=data.blocked_domains,
        blocked_input_patterns=data.blocked_input_patterns,
        blocked_actions=data.blocked_actions,
        trusted_domains=data.trusted_domains,
        max_risk_tolerance=data.max_risk_tolerance,
        require_human_approval=data.require_human_approval,
        rate_limits=data.rate_limits,
    )
    db.add(policy)
    await db.flush()

    logger.info("Created new policy %s for tenant %s", policy.id, tenant_id)
    return policy


async def update_policy(
    db: AsyncSession,
    tenant_id: str,
    data: PolicyUpdate,
) -> Optional[Policy]:
    """
    Partial update of the active policy for a tenant.
    Only fields provided in `data` are modified.
    """
    policy = await get_active_policy(db, tenant_id)
    if not policy:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    policy.updated_at = datetime.now(timezone.utc)

    await db.flush()
    logger.info("Updated policy %s for tenant %s (fields: %s)", policy.id, tenant_id, list(update_data.keys()))
    return policy


# ============================================================================
# Agent Session CRUD
# ============================================================================

async def create_session(
    db: AsyncSession,
    tenant_id: str,
    task_prompt: str,
    target_url: Optional[str] = None,
    user_id: Optional[str] = None,
    queue_name: str = "agents",
    priority: int = 5,
    max_retries: int = 3,
    celery_task_id: Optional[str] = None,
) -> AgentSession:
    """Create a new agent session in CREATED/QUEUED status with full lifecycle tracking."""
    now_str = datetime.now(timezone.utc).isoformat()
    init_event = {
        "from": None,
        "to": SessionStatus.QUEUED.value,
        "timestamp": now_str,
        "reason": "Task submitted via API"
    }
    session = AgentSession(
        tenant_id=tenant_id,
        user_id=user_id,
        task_prompt=task_prompt,
        target_url=target_url,
        queue_name=queue_name,
        priority=priority,
        max_retries=max_retries,
        celery_task_id=celery_task_id,
        status=SessionStatus.QUEUED,
        lifecycle_events=[init_event]
    )
    db.add(session)
    await db.flush()
    logger.info("Created session %s for tenant %s (queue=%s, priority=%d)", session.id, tenant_id, queue_name, priority)
    return session


async def update_session_status(
    db: AsyncSession,
    session_id: str,
    tenant_id: str,
    status: SessionStatus,
    result_summary: Optional[str] = None,
    error_message: Optional[str] = None,
    celery_task_id: Optional[str] = None,
) -> Optional[AgentSession]:
    """Update the status of an agent session with tenant isolation and explicit transition tracking."""
    result = await db.execute(
        select(AgentSession).where(
            AgentSession.id == session_id,
            AgentSession.tenant_id == tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        return None

    old_status = session.status.value if session.status else "UNKNOWN"
    session.status = status
    now = datetime.now(timezone.utc)

    if celery_task_id:
        session.celery_task_id = celery_task_id

    if status == SessionStatus.RUNNING and not session.started_at:
        session.started_at = now
    elif status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED, SessionStatus.TIMED_OUT):
        session.completed_at = now
    elif status == SessionStatus.QUEUED:
        session.completed_at = None
        session.error_message = None

    if status == SessionStatus.RETRYING:
        session.retry_count = (session.retry_count or 0) + 1

    if result_summary is not None:
        session.result_summary = result_summary
    if error_message is not None:
        session.error_message = error_message

    # Track lifecycle transition explicitly (Task 1 & Task 7)
    events = list(session.lifecycle_events) if session.lifecycle_events else []
    events.append({
        "from": old_status,
        "to": status.value,
        "timestamp": now.isoformat(),
        "reason": result_summary or error_message or f"Transitioned to {status.value}",
        "retry_count": session.retry_count
    })
    session.lifecycle_events = events

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "lifecycle_events")

    # Record Phase 6 Prometheus Task & Lifecycle Metrics
    try:
        from security.metrics import record_task_submission, record_task_duration, abs_task_retries_total, abs_dead_letter_tasks_total
        record_task_submission(session.tenant_id, session.queue_name or "default", status.value)
        if status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED, SessionStatus.TIMED_OUT) and session.started_at:
            duration = (now - session.started_at).total_seconds()
            record_task_duration(session.tenant_id, session.queue_name or "default", status.value, duration)
        if status == SessionStatus.RETRYING:
            abs_task_retries_total.labels(tenant_id=session.tenant_id or "unknown", queue_name=session.queue_name or "default").inc()
        if status in (SessionStatus.FAILED, SessionStatus.TIMED_OUT) and session.retry_count and session.retry_count >= 3:
            abs_dead_letter_tasks_total.labels(tenant_id=session.tenant_id or "unknown", queue_name=session.queue_name or "default", reason=status.value).inc()
    except Exception:
        pass

    await db.flush()
    return session


async def count_active_sessions(
    db: AsyncSession, tenant_id: str
) -> int:
    """Count sessions currently in QUEUED, RUNNING, or RETRYING status for a tenant."""
    result = await db.execute(
        select(func.count(AgentSession.id)).where(
            AgentSession.tenant_id == tenant_id,
            AgentSession.status.in_([SessionStatus.QUEUED, SessionStatus.RUNNING, SessionStatus.RETRYING]),
        )
    )
    return result.scalar_one()


async def get_queue_statistics(
    db: AsyncSession, tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """Gather real-time task statistics grouped by status and queue (Task 8 & 9)."""
    query = select(AgentSession.status, func.count(AgentSession.id)).group_by(AgentSession.status)
    if tenant_id:
        query = query.where(AgentSession.tenant_id == tenant_id)

    status_result = await db.execute(query)
    status_counts = {row[0].value if hasattr(row[0], "value") else str(row[0]): int(row[1]) for row in status_result.all()}

    queue_query = select(AgentSession.queue_name, func.count(AgentSession.id)).group_by(AgentSession.queue_name)
    if tenant_id:
        queue_query = queue_query.where(AgentSession.tenant_id == tenant_id)

    queue_result = await db.execute(queue_query)
    queue_counts = {str(row[0] or "agents"): int(row[1]) for row in queue_result.all()}

    total_sessions = sum(status_counts.values())

    return {
        "total_sessions": total_sessions,
        "queued": status_counts.get("QUEUED", 0) + status_counts.get("CREATED", 0),
        "running": status_counts.get("RUNNING", 0),
        "completed": status_counts.get("COMPLETED", 0),
        "failed": status_counts.get("FAILED", 0),
        "cancelled": status_counts.get("CANCELLED", 0),
        "retrying": status_counts.get("RETRYING", 0),
        "timed_out": status_counts.get("TIMED_OUT", 0),
        "by_queue": queue_counts
    }


async def add_telemetry_event(
    db: AsyncSession,
    session_id: str,
    tenant_id: str,
    event_data: dict,
) -> Optional[AgentSession]:
    """Append a telemetry event to a session."""
    result = await db.execute(
        select(AgentSession).where(
            AgentSession.id == session_id,
            AgentSession.tenant_id == tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    
    events = list(session.telemetry_events) if session.telemetry_events else []
    
    # Ensure created_at is injected
    if "timestamp" not in event_data:
        event_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
    events.append(event_data)
    session.telemetry_events = events
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "telemetry_events")
    
    await db.flush()
    return session



async def get_session(
    db: AsyncSession, session_id: str, tenant_id: str
) -> Optional[AgentSession]:
    """Retrieve a session by ID with tenant isolation."""
    result = await db.execute(
        select(AgentSession).where(
            AgentSession.id == session_id,
            AgentSession.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def list_sessions(
    db: AsyncSession,
    tenant_id: str,
    *,
    status: Optional[SessionStatus] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[AgentSession], int]:
    """
    List sessions for a tenant with optional status filter and pagination.

    Returns:
        (list_of_sessions, total_count)
    """
    base_query = select(AgentSession).where(AgentSession.tenant_id == tenant_id)
    count_query = select(func.count(AgentSession.id)).where(AgentSession.tenant_id == tenant_id)

    if status:
        base_query = base_query.where(AgentSession.status == status)
        count_query = count_query.where(AgentSession.status == status)

    # Total count.
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated results.
    offset = (page - 1) * page_size
    result = await db.execute(
        base_query
        .order_by(AgentSession.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    sessions = list(result.scalars().all())
    return sessions, total


async def count_active_sessions(
    db: AsyncSession, tenant_id: str
) -> int:
    """Count sessions currently in QUEUED or RUNNING status for a tenant."""
    result = await db.execute(
        select(func.count(AgentSession.id)).where(
            AgentSession.tenant_id == tenant_id,
            AgentSession.status.in_([SessionStatus.QUEUED, SessionStatus.RUNNING]),
        )
    )
    return result.scalar_one()


# ============================================================================
# Audit Log CRUD
# ============================================================================

async def create_audit_log(
    db: AsyncSession,
    data: AuditLogCreate,
) -> AuditLog:
    """
    Insert a new audit log entry. This is the primary write path used by
    the security engine during agent execution.
    """
    log = AuditLog(
        tenant_id=data.tenant_id,
        session_id=data.session_id,
        event_type=data.event_type,
        url=data.url,
        details=data.details,
        risk_level=RiskLevel(data.risk_level) if data.risk_level else RiskLevel.LOW,
        risk_score=data.risk_score,
        action_taken=ActionTaken(data.action_taken) if data.action_taken else ActionTaken.ALLOWED,
        risk_breakdown=data.risk_breakdown,
        screenshot_path=data.screenshot_path,
        xai_explanation=data.xai_explanation,
        xai_pending=data.xai_pending,
    )
    db.add(log)
    await db.flush()

    # Record Phase 6 Prometheus Security & Action Metrics
    try:
        from security.metrics import abs_agent_actions_total, record_security_event_metric
        abs_agent_actions_total.labels(
            tenant_id=data.tenant_id or "anonymous",
            action_type=data.event_type or "general",
            verdict=log.action_taken.value if log.action_taken else "ALLOWED"
        ).inc()
        if log.action_taken in (ActionTaken.BLOCKED, ActionTaken.FLAGGED) or (log.risk_score and log.risk_score >= 50):
            record_security_event_metric(
                data.tenant_id or "anonymous",
                data.event_type or "security_violation",
                "HIGH" if (log.risk_score and log.risk_score >= 75) else "MEDIUM"
            )
    except Exception:
        pass

    return log


async def update_audit_xai_explanation(
    db: AsyncSession,
    log_id: str,
    explanation: str,
) -> bool:
    """
    Backfill the XAI explanation for an audit log entry.
    Called by the Celery worker after Gemini generates the explanation.
    """
    result = await db.execute(
        update(AuditLog)
        .where(AuditLog.id == log_id)
        .values(
            xai_explanation=explanation,
            xai_pending=False,
        )
    )
    return result.rowcount > 0


async def list_audit_logs(
    db: AsyncSession,
    tenant_id: str,
    *,
    session_id: Optional[str] = None,
    risk_level: Optional[RiskLevel] = None,
    event_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[AuditLog], int]:
    """
    List audit logs for a tenant with optional filters and pagination.

    Returns:
        (list_of_logs, total_count)
    """
    base_query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    count_query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)

    if session_id:
        base_query = base_query.where(AuditLog.session_id == session_id)
        count_query = count_query.where(AuditLog.session_id == session_id)
    if risk_level:
        base_query = base_query.where(AuditLog.risk_level == risk_level)
        count_query = count_query.where(AuditLog.risk_level == risk_level)
    if event_type:
        base_query = base_query.where(AuditLog.event_type == event_type)
        count_query = count_query.where(AuditLog.event_type == event_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        base_query
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = list(result.scalars().all())
    return logs, total


async def get_audit_stats(
    db: AsyncSession, tenant_id: str
) -> dict:
    """
    Aggregate security statistics for a tenant's dashboard.
    Returns counts by risk level, event type, and action taken.
    """
    # Total events.
    total_result = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant_id)
    )
    total = total_result.scalar_one()

    # By risk level.
    risk_result = await db.execute(
        select(AuditLog.risk_level, func.count(AuditLog.id))
        .where(AuditLog.tenant_id == tenant_id)
        .group_by(AuditLog.risk_level)
    )
    risk_counts = {str(row[0].value if hasattr(row[0], 'value') else row[0]): row[1] for row in risk_result.all()}

    # Average risk score.
    avg_result = await db.execute(
        select(func.avg(AuditLog.risk_score)).where(AuditLog.tenant_id == tenant_id)
    )
    avg_risk = avg_result.scalar_one() or 0

    # Top event types.
    type_result = await db.execute(
        select(AuditLog.event_type, func.count(AuditLog.id))
        .where(AuditLog.tenant_id == tenant_id)
        .group_by(AuditLog.event_type)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    top_event_types = {row[0]: row[1] for row in type_result.all()}

    return {
        "total_events": total,
        "risk_distribution": risk_counts,
        "average_risk_score": round(float(avg_risk), 1),
        "top_event_types": top_event_types,
    }


# ── Analytics ────────────────────────────────────
async def get_time_series_stats(
    db: AsyncSession,
    tenant_id: str,
    days: int = 30
) -> list[dict]:
    """Get daily counts of safe vs blocked actions for chart data."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from db.models import AuditLog

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    results = await db.execute(
        select(AuditLog.created_at, AuditLog.action_taken, AuditLog.risk_score).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.created_at >= cutoff
        )
    )
    rows = results.all()

    # Initialize dictionary for each of the last `days` days so timeline is continuous
    daily_stats = {}
    for d in range(days - 1, -1, -1):
        dt_key = (now - timedelta(days=d)).strftime('%Y-%m-%d')
        daily_stats[dt_key] = {'total': 0, 'safe': 0, 'blocked': 0, 'risk_sum': 0}

    for row in rows:
        created_at = row.created_at
        if hasattr(created_at, 'strftime'):
            dt_str = created_at.strftime('%Y-%m-%d')
        else:
            dt_str = str(created_at)[:10]

        if dt_str not in daily_stats:
            daily_stats[dt_str] = {'total': 0, 'safe': 0, 'blocked': 0, 'risk_sum': 0}

        st = daily_stats[dt_str]
        st['total'] += 1
        st['risk_sum'] += (row.risk_score or 0)

        action = str(row.action_taken)
        if hasattr(row.action_taken, 'value'):
            action = row.action_taken.value
        if action in ('ALLOWED', 'MONITOR', 'ActionTaken.ALLOWED', 'ActionTaken.MONITOR'):
            st['safe'] += 1
        else:
            st['blocked'] += 1

    output = []
    for dt_str in sorted(daily_stats.keys()):
        st = daily_stats[dt_str]
        avg_r = round(st['risk_sum'] / st['total'], 1) if st['total'] > 0 else 0.0
        output.append({
            'date': dt_str,
            'total': st['total'],
            'safe': st['safe'],
            'blocked': st['blocked'],
            'avg_risk': avg_r
        })
    return output


async def get_recent_incidents(
    db: AsyncSession,
    tenant_id: str,
    limit: int = 10
) -> list:
    """Get recent audit log entries for live feed."""
    from sqlalchemy import select
    from db.models import AuditLog
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_xai_audit_logs(
    db: AsyncSession,
    tenant_id: str,
    page: int = 1,
    page_size: int = 20,
    pending_only: bool = False
) -> tuple[list, int]:
    """Get audit logs with XAI explanations."""
    from sqlalchemy import select, func
    from db.models import AuditLog
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    count_query = select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == tenant_id)

    if pending_only:
        query = query.where(AuditLog.xai_pending == True)
        count_query = count_query.where(AuditLog.xai_pending == True)
    else:
        query = query.where(AuditLog.xai_explanation.isnot(None))
        count_query = count_query.where(AuditLog.xai_explanation.isnot(None))

    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = list(result.scalars().all())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return logs, total

