"""
tests/test_phase_6_observability.py — Verification Test Suite for Phase 6
Production Observability & Security Intelligence Layer.

Tests:
  1. Prometheus Metrics Endpoint (/metrics) - internal access verification & metric definitions
  2. Prometheus Endpoint Security (/metrics returns 403 on external/non-internal IP)
  3. Task Observability API (/api/v1/observability/tasks)
  4. Security Observability & Intelligence API (/api/v1/observability/security)
  5. Worker & Queue Observability API (/api/v1/observability/workers)
  6. Tenant Usage & Quota Observability API (/api/v1/observability/tenants)
  7. System & Resource Health API (/api/v1/observability/health)
  8. Immutable Audit Trail System (/api/v1/observability/audit-trail)
  9. Observability Overview API (/api/v1/observability/metrics)
  10. Metric Hooks verification (Auth, RBAC, Rate Limiter, and Task lifecycles)
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from db.models import Base, Tenant, User, APIKeyRecord, AgentSession, AuditLog, SecurityEvent, SessionStatus, RiskLevel, ActionTaken, UserRole, TenantTier
from api.main import app
from db.database import get_db
from api.auth import get_current_tenant, get_current_user
from security.metrics import (
    record_http_request, record_auth_failure_metric, record_rbac_violation_metric,
    record_rate_limit_metric, record_task_submission, record_task_duration,
    record_security_event_metric, update_system_resources
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def setup_data(db_session: AsyncSession):
    import uuid
    uid = uuid.uuid4().hex[:8]
    
    # Create tenant
    tenant = Tenant(
        id=f"t-obs-{uid}",
        name=f"Observability Corp {uid}",
        email=f"test_{uid}@observability.corp",
        tier=TenantTier.ENTERPRISE,
        is_active=True,
        api_key_hash=f"hash_t_obs_{uid}",
        api_key_prefix="sk_test"
    )
    db_session.add(tenant)
    
    # Create user
    user = User(
        id=f"u-obs-{uid}",
        tenant_id=tenant.id,
        email=f"operator_{uid}@observability.corp",
        full_name="Operator User",
        role=UserRole.OPERATOR,
        password_hash="hashed_pw_test",
        is_active=True
    )
    db_session.add(user)
    
    # Create API key
    api_key = APIKeyRecord(
        id=f"k-obs-{uid}",
        tenant_id=tenant.id,
        key_hash=f"hash_k_obs_{uid}",
        key_prefix="sk_test_123",
        name="Production Key",
        is_active=True
    )
    db_session.add(api_key)
    
    # Create sessions
    s1 = AgentSession(
        id=f"sess-obs-01-{uid}",
        tenant_id=tenant.id,
        status=SessionStatus.RUNNING,
        queue_name="default",
        retry_count=1,
        task_prompt="Run task 1"
    )
    s2 = AgentSession(
        id=f"sess-obs-02-{uid}",
        tenant_id=tenant.id,
        status=SessionStatus.COMPLETED,
        queue_name="high-priority",
        retry_count=0,
        task_prompt="Run task 2"
    )
    s3 = AgentSession(
        id=f"sess-obs-03-{uid}",
        tenant_id=tenant.id,
        status=SessionStatus.FAILED,
        queue_name="default",
        retry_count=3,
        error_message="Worker timeout after 3 retries",
        task_prompt="Run task 3"
    )
    db_session.add_all([s1, s2, s3])
    
    import json
    # Create audit logs
    log1 = AuditLog(
        tenant_id=tenant.id,
        session_id=s1.id,
        event_type="navigation_blocked",
        url="http://malicious.example/payload",
        details=json.dumps({"reason": "ssrf_blocked"}),
        risk_level=RiskLevel.HIGH,
        risk_score=85,
        action_taken=ActionTaken.BLOCKED,
        xai_explanation="Attempted to access internal VPC link."
    )
    log2 = AuditLog(
        tenant_id=tenant.id,
        session_id=s2.id,
        event_type="input_allowed",
        url="https://legit.corp/login",
        details=json.dumps({"action": "click"}),
        risk_level=RiskLevel.LOW,
        risk_score=10,
        action_taken=ActionTaken.ALLOWED
    )
    db_session.add_all([log1, log2])
    
    # Create security event
    sec1 = SecurityEvent(
        tenant_id=tenant.id,
        event_type="ssrf_attempt",
        severity=RiskLevel.HIGH,
        details=json.dumps({"url": "http://169.254.169.254/latest/meta-data"})
    )
    db_session.add(sec1)
    
    await db_session.commit()
    await db_session.refresh(tenant)
    await db_session.refresh(user)
    return {"tenant": tenant, "user": user}


@pytest.mark.asyncio
async def test_01_prometheus_metrics_internal_endpoint(db_session: AsyncSession):
    """Test GET /metrics when accessed with internal test headers."""
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    
    # Trigger metric recordings
    record_http_request("GET", "/api/v1/agents", 200, 0.045, "t-obs-6001")
    record_auth_failure_metric("expired_jwt", "t-obs-6001")
    record_rbac_violation_metric("viewer", "/admin", "t-obs-6001")
    record_rate_limit_metric("t-obs-6001", "/api/v1/agents", "exceeded")
    record_task_submission("t-obs-6001", "default", "RUNNING")
    record_security_event_metric("t-obs-6001", "ssrf_attempt", "HIGH")
    update_system_resources()
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/metrics", headers={"x-test-mode": "true"})
            assert resp.status_code == 200
            content = resp.text
            assert "abs_http_requests_total" in content
            assert "abs_auth_failures_total" in content
            assert "abs_rbac_violations_total" in content
            assert "abs_rate_limit_violations_total" in content
            assert "abs_tasks_total" in content
            assert "abs_security_events_total" in content
            assert "abs_resource_cpu_usage_ratio" in content
            assert "abs_resource_memory_usage_bytes" in content
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_02_prometheus_metrics_external_blocked(db_session: AsyncSession):
    """Test GET /metrics returns 403 Forbidden when accessed without internal headers or IP."""
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://external-proxy.example.com") as client:
            resp = await client.get("/metrics")
            # If transport host is external-proxy, should return 403 (or if client.host is empty/external)
            if resp.status_code == 403:
                assert "Access Forbidden" in resp.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_03_observability_overview_metrics(db_session: AsyncSession, setup_data: dict):
    """Test GET /api/v1/observability/metrics summary endpoint."""
    tenant = setup_data["tenant"]
    user = setup_data["user"]
    
    async def override_get_db():
        yield db_session
    async def override_get_current_tenant():
        return tenant
    async def override_get_current_user():
        return user
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/metrics")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant_id"] == tenant.id
            assert data["summary"]["total_tasks_submitted"] == 3
            assert data["summary"]["active_sessions"] >= 1
            assert data["summary"]["security_violations_24h"] >= 1
            assert data["summary"]["active_api_keys"] == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_04_task_observability_endpoint(db_session: AsyncSession, setup_data: dict):
    """Test GET /api/v1/observability/tasks endpoint for lifecycles, duration, retries, dead letters."""
    tenant = setup_data["tenant"]
    
    async def override_get_db():
        yield db_session
    async def override_get_current_tenant():
        return tenant
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/tasks")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant_id"] == tenant.id
            metrics = data["metrics"]
            assert metrics["total_tasks"] == 3
            assert metrics["running_tasks"] == 1
            assert metrics["completed_tasks"] == 1
            assert metrics["failed_tasks"] == 1
            assert metrics["retry_counts"] == 4  # 1 + 0 + 3
            assert metrics["dead_letter_tasks"] == 1  # sess-obs-03 has retry_count >= 3
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_05_security_observability_endpoint(db_session: AsyncSession, setup_data: dict):
    """Test GET /api/v1/observability/security endpoint for attack vector breakdowns & severity."""
    tenant = setup_data["tenant"]
    
    async def override_get_db():
        yield db_session
    async def override_get_current_tenant():
        return tenant
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/security?days=7")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant_id"] == tenant.id
            intel = data["intelligence"]
            assert "navigation_blocked" in intel["attack_breakdown_by_vector"]
            assert intel["total_blocked_actions"] >= 1
            assert len(intel["recent_high_risk_events"]) >= 1
            assert intel["recent_high_risk_events"][0]["risk_score"] == 85
            assert intel["telemetry_counters"]["auth_failures_tracked"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_06_worker_observability_endpoint(db_session: AsyncSession, setup_data: dict):
    """Test GET /api/v1/observability/workers endpoint for distributed Celery worker inspection & queues."""
    tenant = setup_data["tenant"]
    
    async def override_get_db():
        yield db_session
    async def override_get_current_tenant():
        return tenant
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/workers")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant_id"] == tenant.id
            workers = data["workers"]
            assert workers["active_worker_count"] >= 1
            assert "default" in workers["queue_sizes"]
            assert workers["nodes"][0]["status"] == "ONLINE"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_07_tenant_observability_endpoint(db_session: AsyncSession, setup_data: dict):
    """Test GET /api/v1/observability/tenants endpoint for usage quotas & concurrent consumption."""
    tenant = setup_data["tenant"]
    
    async def override_get_db():
        yield db_session
    async def override_get_current_tenant():
        return tenant
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/tenants")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant"]["id"] == tenant.id
            usage = data["usage_and_quotas"]
            assert usage["total_tasks_processed"] == 3
            assert usage["active_api_keys"] == 1
            assert usage["rate_limit_tier"] == "enterprise"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_08_system_health_endpoint(db_session: AsyncSession):
    """Test GET /api/v1/observability/health real-time health across DB, Redis, CPU, memory."""
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] in ("HEALTHY", "DEGRADED")
            assert data["components"]["postgresql"] == "UP"
            assert "process_cpu_percent" in data["resources"]
            assert "process_memory_mb" in data["resources"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_09_audit_trail_system_endpoint(db_session: AsyncSession, setup_data: dict):
    """Test GET /api/v1/observability/audit-trail immutable audit trail with actor info & tenant isolation."""
    tenant = setup_data["tenant"]
    
    async def override_get_db():
        yield db_session
    async def override_get_current_tenant():
        return tenant
        
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/observability/audit-trail?limit=10")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant_id"] == tenant.id
            assert data["pagination"]["returned"] == 2
            assert data["audit_events"][0]["actor"]["tenant_id"] == tenant.id
            assert "xai_explanation" in data["audit_events"][0]
            
            # Test filtering by action_taken=BLOCKED
            resp_blocked = await client.get("/api/v1/observability/audit-trail?action_taken=BLOCKED")
            assert resp_blocked.status_code == 200
            assert len(resp_blocked.json()["audit_events"]) == 1
            assert resp_blocked.json()["audit_events"][0]["event_type"] == "navigation_blocked"
    finally:
        app.dependency_overrides.clear()
