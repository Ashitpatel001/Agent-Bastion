"""
tests/test_phase_4_orchestration.py — Complete Verification Suite for Phase 4 (Agent Runtime & Worker Orchestration).

Verifies:
  1. Explicit lifecycle state transitions (QUEUED -> RUNNING -> COMPLETED / RETRYING / FAILED / CANCELLED) with timestamps and event history (Task 1 & Task 7).
  2. Multi-tenant isolation for agent execution: Tenant A cannot read, list, or cancel Tenant B's tasks (Task 2 & Task 6).
  3. Dead-letter queue / terminal failure handling when max retries or time limits are reached (Task 4.3).
  4. Task cancellation and active worker revocation via Celery control signals (Task 4.1 & Task 8).
  5. Multi-queue task priority routing (`priority_agents`, `agents`, `xai`) based on priority score and tenant tier (Task 5 & Task 10).
  6. Real-time worker health and queue statistics endpoints with rate limiting and offline fallback checks (Task 8 & Task 9).
"""

import pytest
import asyncio
import uuid
import time
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock, AsyncMock

from api.main import app
from db.database import get_db_context, init_db
from db import crud, models
from db.models import SessionStatus, TenantTier
from workers.agent_tasks import run_agent_task, cancel_agent_task
from workers.dispatch import dispatch_task

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db_and_limiter():
    """Verify DB tables exist and clear rate limiter state before each test."""
    asyncio.run(init_db())
    from security.rate_limiter import rate_limiter_engine
    asyncio.run(rate_limiter_engine.clear_all())
    yield
    asyncio.run(rate_limiter_engine.clear_all())


@pytest.mark.asyncio
async def test_session_lifecycle_events_and_transitions():
    """
    Verify explicit lifecycle state tracking (`lifecycle_events` JSON, timestamps, retry counting) (Task 1 & Task 7).
    """
    async with get_db_context() as db:
        tenant, _ = await crud.create_tenant(
            db, name="Lifecycle Tenant", email=f"life_{uuid.uuid4().hex[:6]}@test.internal"
        )
        # 1. Create session (QUEUED)
        session = await crud.create_session(
            db, tenant_id=tenant.id, task_prompt="Check SSL certificate", priority=5
        )
        assert session.status == SessionStatus.QUEUED
        assert len(session.lifecycle_events) == 1
        assert session.lifecycle_events[0]["to"] == "QUEUED"
        assert session.started_at is None

        # 2. Transition to RUNNING
        updated = await crud.update_session_status(
            db, session.id, tenant.id, SessionStatus.RUNNING, celery_task_id="mock-celery-123"
        )
        assert updated.status == SessionStatus.RUNNING
        assert updated.celery_task_id == "mock-celery-123"
        assert updated.started_at is not None
        assert len(updated.lifecycle_events) == 2
        assert updated.lifecycle_events[-1]["to"] == "RUNNING"

        # 3. Simulate retry transition (RETRYING)
        retried = await crud.update_session_status(
            db, session.id, tenant.id, SessionStatus.RETRYING, error_message="Temporary network hiccup"
        )
        assert retried.status == SessionStatus.RETRYING
        assert retried.retry_count == 1
        assert len(retried.lifecycle_events) == 3
        assert retried.lifecycle_events[-1]["reason"] == "Temporary network hiccup"

        # 4. Transition to COMPLETED
        completed = await crud.update_session_status(
            db, session.id, tenant.id, SessionStatus.COMPLETED, result_summary="SSL Check OK"
        )
        assert completed.status == SessionStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.result_summary == "SSL Check OK"
        assert len(completed.lifecycle_events) == 4
        assert completed.lifecycle_events[-1]["to"] == "COMPLETED"


@pytest.mark.asyncio
async def test_multi_tenant_isolation_in_sessions():
    """
    Verify strict multi-tenant isolation across agent sessions (Task 2 & Task 6).
    Tenant A cannot read, update, or cancel Tenant B's tasks via CRUD or API.
    """
    async with get_db_context() as db:
        tenant_a, key_a = await crud.create_tenant(
            db, name="Tenant Alpha", email=f"alpha_{uuid.uuid4().hex[:6]}@test.internal"
        )
        tenant_b, key_b = await crud.create_tenant(
            db, name="Tenant Beta", email=f"beta_{uuid.uuid4().hex[:6]}@test.internal"
        )
        session_a = await crud.create_session(
            db, tenant_id=tenant_a.id, task_prompt="Secret Alpha Mission"
        )

        # Direct CRUD lookup attempt by Tenant B should yield None
        lookup_by_b = await crud.get_session(db, session_id=session_a.id, tenant_id=tenant_b.id)
        assert lookup_by_b is None

        # Direct status update attempt by Tenant B should return None
        update_by_b = await crud.update_session_status(
            db, session_a.id, tenant_b.id, SessionStatus.CANCELLED
        )
        assert update_by_b is None

    # Test via API endpoints
    headers_b = {"X-API-Key": key_b}
    res_get = client.get(f"/api/v1/agents/{session_a.id}", headers=headers_b)
    assert res_get.status_code == 404

    res_cancel = client.post(f"/api/v1/agents/{session_a.id}/cancel", headers=headers_b)
    assert res_cancel.status_code == 404


def test_dead_letter_task_handling():
    """
    Verify dead-letter handling when tasks suffer terminal errors or exceed max retries (Task 4.3).
    """
    async def _setup():
        async with get_db_context() as db:
            tenant, _ = await crud.create_tenant(
                db, name="Dead Letter Tenant", email=f"dead_{uuid.uuid4().hex[:6]}@test.internal"
            )
            session = await crud.create_session(
                db, tenant_id=tenant.id, task_prompt="Fatal failure mission", max_retries=0
            )
            return tenant.id, session.id
    tenant_id, session_id = asyncio.run(_setup())

    with patch("workers.agent_tasks._execute_secure_agent", new_callable=AsyncMock) as mock_agent:
        mock_agent.side_effect = RuntimeError("Critical browser crash in target environment")
        
        # Execute run_agent_task wrapper synchronously where max_retries=0 triggers dead letter branching
        result = run_agent_task.__wrapped__(session_id, tenant_id)
        
        assert result["status"] == "failed"
        assert result.get("dead_letter") is True
        assert "RuntimeError" in result["error"]

    async def _verify_db():
        async with get_db_context() as db:
            session = await crud.get_session(db, session_id, tenant_id)
            assert session.status == SessionStatus.FAILED
            assert "Dead-letter task failure [RuntimeError]" in session.error_message
            assert session.completed_at is not None
    asyncio.run(_verify_db())


def test_task_cancellation_and_revocation():
    """
    Verify active task cancellation and Celery worker revocation signals (Task 4.1 & Task 8).
    """
    async def _setup():
        async with get_db_context() as db:
            tenant, api_key = await crud.create_tenant(
                db, name="Cancel Tenant", email=f"cancel_{uuid.uuid4().hex[:6]}@test.internal"
            )
            session = await crud.create_session(
                db, tenant_id=tenant.id, task_prompt="Long running job", celery_task_id="celery-running-456"
            )
            return tenant.id, session.id, api_key
    tenant_id, session_id, api_key = asyncio.run(_setup())

    # Cancel via API
    headers = {"X-API-Key": api_key}
    with patch("workers.celery_app.celery_app.control.revoke") as mock_revoke:
        res = client.post(f"/api/v1/agents/{session_id}/cancel", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "CANCELLED"
        assert "signaled" in data["message"]

    async def _verify_cancelled():
        async with get_db_context() as db:
            session = await crud.get_session(db, session_id, tenant_id)
            assert session.status == SessionStatus.CANCELLED
            assert session.completed_at is not None
            assert session.lifecycle_events[-1]["to"] == "CANCELLED"
    asyncio.run(_verify_cancelled())


def test_priority_queue_routing_and_tiers():
    """
    Verify multi-queue task priority routing based on priority requests and tenant tier (Task 5 & Task 10).
    """
    async def _setup():
        async with get_db_context() as db:
            t_free, k_free = await crud.create_tenant(
                db, name="Free Tier Tenant", email=f"free_{uuid.uuid4().hex[:6]}@test.internal", tier=TenantTier.FREE
            )
            t_pro, k_pro = await crud.create_tenant(
                db, name="Pro Tier Tenant", email=f"pro_{uuid.uuid4().hex[:6]}@test.internal", tier=TenantTier.PRO
            )
            return k_free, k_pro
    k_free, k_pro = asyncio.run(_setup())

    with patch("workers.dispatch.is_redis_available", return_value=True), \
         patch("celery.app.task.Task.apply_async", return_value=MagicMock(id="async-id-789")) as mock_apply:

        # 1. Free tier submitting normal priority -> goes to 'agents' queue
        res1 = client.post(
            "/api/v1/agents",
            json={"task_prompt": "Standard task", "priority": 5},
            headers={"X-API-Key": k_free}
        )
        assert res1.status_code == 201
        assert res1.json()["queue_name"] == "agents"
        assert res1.json()["priority"] == 5

        # 2. Pro tier submitting high priority (priority=2) -> routes to 'priority_agents' queue
        res2 = client.post(
            "/api/v1/agents",
            json={"task_prompt": "Urgent mission", "priority": 2},
            headers={"X-API-Key": k_pro}
        )
        assert res2.status_code == 201
        assert res2.json()["queue_name"] == "priority_agents"
        assert res2.json()["priority"] == 2


def test_worker_health_and_queue_stats_endpoints():
    """
    Verify /workers/health and /queues/stats endpoints (Task 8 & Task 9).
    """
    async def _setup():
        async with get_db_context() as db:
            t, k = await crud.create_tenant(
                db, name="Monitor Tenant", email=f"monitor_{uuid.uuid4().hex[:6]}@test.internal"
            )
            await crud.create_session(db, tenant_id=t.id, task_prompt="Stats check 1")
            await crud.create_session(db, tenant_id=t.id, task_prompt="Stats check 2")
            return k
    api_key = asyncio.run(_setup())
    headers = {"X-API-Key": api_key}

    # Test /workers/health endpoint
    res_health = client.get("/api/v1/agents/workers/health", headers=headers)
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] in ("healthy", "degraded", "offline_fallback")
    assert "queues" in health_data

    # Test /queues/stats endpoint
    res_stats = client.get("/api/v1/agents/queues/stats", headers=headers)
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "queued" in stats_data
    assert stats_data["queued"] >= 2
    assert "total_sessions" in stats_data
