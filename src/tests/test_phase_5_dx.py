import pytest
import uuid
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from api.main import app
from db.database import get_db_context
from db import crud
from db.models import TenantTier, SessionStatus, User, UserRole

client = TestClient(app)


def test_dx_quickstart_and_onboarding_progress():
    """
    Verify /api/v1/dx/quickstart returns step-by-step onboarding progress and SDK code snippets (Task 7 & Task 8).
    """
    async def _setup():
        async with get_db_context() as db:
            tenant, api_key = await crud.create_tenant(
                db, name="Quickstart DX Tenant", email=f"dx_{uuid.uuid4().hex[:6]}@test.internal", tier=TenantTier.PRO
            )
            return tenant.id, api_key
    tenant_id, api_key = asyncio.run(_setup())
    headers = {"X-API-Key": api_key}

    # Query quickstart progress right after creation (no API keys or sessions yet via this route)
    res = client.get("/api/v1/dx/quickstart", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["tenant_id"] == tenant_id
    assert data["tenant_name"] == "Quickstart DX Tenant"
    assert data["tier"] == "PRO"
    assert len(data["steps"]) == 5
    assert data["steps"][0]["id"] == "step_1_docker"
    assert data["steps"][1]["id"] == "step_2_admin"
    assert data["steps"][2]["id"] == "step_3_api_key"
    assert data["steps"][3]["id"] == "step_4_submit"
    
    # Verify code snippets are generated properly
    assert "curl" in data["code_examples"]
    assert "python_sdk" in data["code_examples"]
    assert "javascript_sdk" in data["code_examples"]
    assert "from abss import AgentBastionClient" in data["code_examples"]["python_sdk"]
    assert "import { AgentBastion } from '@abss/sdk'" in data["code_examples"]["javascript_sdk"]


def test_dx_unified_dashboard_overview():
    """
    Verify /api/v1/dx/overview aggregates session statistics, worker health, and rate limits (Task 1 & Task 5).
    """
    async def _setup():
        async with get_db_context() as db:
            tenant, api_key = await crud.create_tenant(
                db, name="Overview DX Tenant", email=f"ov_{uuid.uuid4().hex[:6]}@test.internal", tier=TenantTier.ENTERPRISE
            )
            # Create a few sessions in various states
            s1 = await crud.create_session(db, tenant_id=tenant.id, task_prompt="Queued task")
            s2 = await crud.create_session(db, tenant_id=tenant.id, task_prompt="Completed task")
            await crud.update_session_status(db, s2.id, tenant.id, SessionStatus.COMPLETED, result_summary="Done")
            s3 = await crud.create_session(db, tenant_id=tenant.id, task_prompt="Failed task")
            await crud.update_session_status(db, s3.id, tenant.id, SessionStatus.FAILED, error_message="Fatal error")
            return tenant.id, api_key
    tenant_id, api_key = asyncio.run(_setup())
    headers = {"X-API-Key": api_key}

    res = client.get("/api/v1/dx/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["tenant"]["id"] == tenant_id
    assert data["tenant"]["tier"] == "ENTERPRISE"
    assert data["sessions_summary"]["total"] >= 3
    assert data["sessions_summary"]["queued"] >= 1
    assert data["sessions_summary"]["completed"] >= 1
    assert data["sessions_summary"]["failed"] >= 1
    assert "worker_health" in data
    assert "recent_sessions" in data
    assert len(data["recent_sessions"]) <= 5
    assert data["rate_limits"]["max_concurrent_tasks"] == 100


def test_api_key_lifecycle_and_management():
    """
    Verify complete API Key management lifecycle: create, list, rotate, and revoke (Task 3).
    """
    async def _setup():
        async with get_db_context() as db:
            tenant, _ = await crud.create_tenant(
                db, name="API Key DX Tenant", email=f"keys_{uuid.uuid4().hex[:6]}@test.internal"
            )
            user = User(
                tenant_id=tenant.id, email=f"admin_{uuid.uuid4().hex[:6]}@abss.internal",
                hashed_password="hashed_pw_test", full_name="Admin User", role=UserRole.ADMIN
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            from api.auth import create_access_token
            token = create_access_token({"sub": user.id, "tenant_id": tenant.id, "role": user.role.value})
            return tenant.id, token
    tenant_id, token = asyncio.run(_setup())
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create new API Key
    create_res = client.post(
        "/api/v1/api-keys",
        json={"name": "Production Deploy Key", "scopes": ["agents:write", "agents:read"]},
        headers=headers
    )
    assert create_res.status_code == 201
    key_data = create_res.json()
    assert key_data["name"] == "Production Deploy Key"
    assert key_data["raw_key"].startswith("abs_")
    key_id = key_data["id"]

    # 2. List API Keys
    list_res = client.get("/api/v1/api-keys", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(k["id"] == key_id for k in list_data["items"])

    # 3. Rotate API Key
    rotate_res = client.post(f"/api/v1/api-keys/{key_id}/rotate", headers=headers)
    assert rotate_res.status_code == 200
    rotated_data = rotate_res.json()
    assert rotated_data["id"] == key_id
    assert rotated_data["raw_key"].startswith("abs_")
    assert rotated_data["raw_key"] != key_data["raw_key"]

    # 4. Revoke API Key
    revoke_res = client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert revoke_res.status_code == 204


def test_task_management_and_retry_workflow():
    """
    Verify task submission, cancellation, and clean re-enqueuing of failed tasks via /retry (Task 4).
    """
    async def _setup():
        async with get_db_context() as db:
            tenant, api_key = await crud.create_tenant(
                db, name="Retry DX Tenant", email=f"retry_{uuid.uuid4().hex[:6]}@test.internal"
            )
            session = await crud.create_session(db, tenant_id=tenant.id, task_prompt="Faulty job")
            await crud.update_session_status(db, session.id, tenant.id, SessionStatus.FAILED, error_message="Simulated crash")
            return tenant.id, api_key, session.id
    tenant_id, api_key, session_id = asyncio.run(_setup())
    headers = {"X-API-Key": api_key}

    mock_result = MagicMock()
    mock_result.id = "mock-celery-task-id-123"
    with patch("workers.dispatch.is_redis_available", return_value=True), \
         patch("celery.app.task.Task.apply_async", return_value=mock_result):
         
        # Retry failed task
        res = client.post(f"/api/v1/agents/{session_id}/retry", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == session_id
        assert data["status"] == "QUEUED"
        assert data["retry_count"] >= 1
        assert "requeued" in data["message"]

    # Verify session DB status is reset to QUEUED and error is cleared
    async def _verify_db():
        async with get_db_context() as db:
            session = await crud.get_session(db, session_id, tenant_id)
            assert session.status == SessionStatus.QUEUED
            assert session.error_message is None
            assert session.retry_count >= 1
    import time; time.sleep(0.05)
    asyncio.run(_verify_db())


def test_worker_visibility_and_queue_inspection():
    """
    Verify developer operational visibility endpoints for queues and worker nodes (Task 5).
    """
    async def _setup():
        async with get_db_context() as db:
            t, k = await crud.create_tenant(
                db, name="Worker DX Tenant", email=f"wdx_{uuid.uuid4().hex[:6]}@test.internal"
            )
            return k
    api_key = asyncio.run(_setup())
    headers = {"X-API-Key": api_key}

    res_health = client.get("/api/v1/agents/workers/health", headers=headers)
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert "status" in health_data
    assert "queues" in health_data
    assert "active_workers" in health_data

    res_stats = client.get("/api/v1/agents/queues/stats", headers=headers)
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "queued" in stats_data
    assert "running" in stats_data
    assert "total_sessions" in stats_data


def test_realtime_sse_event_stream_connection():
    """
    Verify SSE event stream returns proper content type and connection confirmation (Task 5.8).
    """
    async def _setup():
        async with get_db_context() as db:
            t, k = await crud.create_tenant(
                db, name="SSE DX Tenant", email=f"sse_{uuid.uuid4().hex[:6]}@test.internal"
            )
            return k
    api_key = asyncio.run(_setup())
    headers = {"X-API-Key": api_key, "X-Test-Mode": "true"}

    with client.stream("GET", "/api/v1/dx/events/stream", headers=headers) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Read the first chunk yielded by the generator
        lines = []
        for line in response.iter_lines():
            if line:
                lines.append(line)
            if len(lines) >= 2:
                break
                
        assert any("event: connected" in l for l in lines)
        assert any("stream_active" in l for l in lines)
