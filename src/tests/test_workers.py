"""
tests/test_workers.py — Verification script for Component 4 (Async XAI & Workers).

Run with:
    python -m pytest tests/test_workers.py -v

Or standalone:
    python tests/test_workers.py
"""

import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force SQLite in-memory for testing — no files created.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

passed = 0
failed = 0

def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {detail}")
        failed += 1

async def async_setup():
    from db.database import init_db, get_db_context
    from db import crud
    from db.schemas import AuditLogCreate

    await init_db()

    async with get_db_context() as db:
        tenant, _ = await crud.create_tenant(db, name="Worker Test Tenant", email="worker@test.com")
        tenant_id = tenant.id
        
        session = await crud.create_session(db, tenant_id=tenant_id, task_prompt="Test agent task", target_url="http://test.com")
        session_id = session.id
        
        log_data = AuditLogCreate(
            tenant_id=tenant_id,
            session_id=session_id,
            event_type="XAI_EXPLANATION",
            url="http://test.com",
            details="Blocked action",
            risk_level="HIGH",
            risk_score=95,
            action_taken="BLOCKED",
            xai_pending=True,
        )
        audit_log = await crud.create_audit_log(db, log_data)
        log_id = audit_log.id
        
        cancel_session = await crud.create_session(db, tenant_id=tenant_id, task_prompt="Cancel me")
        cancel_session_id = cancel_session.id
        
    return tenant_id, session_id, log_id, cancel_session_id

def sync_execute_tasks(tenant_id, session_id, log_id, cancel_session_id):
    print("\n--- Testing XAI Tasks ---")
    from workers.xai_tasks import generate_xai_explanation
    from workers.agent_tasks import run_agent_task, cancel_agent_task
    
    with patch("workers.xai_tasks._generate_explanation_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "This is a mocked XAI explanation."
        payload = {"action_data": "{}", "risk_score": 95, "reason": "Test", "risk_level": "HIGH", "breakdown": {}}
        
        # __wrapped__ is bound, so self is already passed
        result = generate_xai_explanation.__wrapped__(log_id, payload)
        
        check("XAI task returns completed status", result.get("status") == "completed")
        check("XAI task returns explanation length", result.get("explanation_length", 0) > 0)

    print("\n--- Testing Agent Tasks ---")
    with patch("workers.agent_tasks._execute_secure_agent", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = "Mocked agent execution completed."
        
        # __wrapped__ is bound, so self is already passed
        result = run_agent_task.__wrapped__(session_id, tenant_id)
        
        check("Agent task returns completed status", result.get("status") == "completed")
        check("Agent task returns result summary", result.get("result_summary") == "Mocked agent execution completed.")

    print("\n--- Testing Task Cancellation ---")
    # cancel_agent_task is NOT a Celery task but a sync helper
    cancel_result = cancel_agent_task(cancel_session_id, tenant_id)
    check("Cancel task returns cancelled status", cancel_result.get("status") == "cancelled")

async def async_verify(tenant_id, session_id, log_id, cancel_session_id):
    from db.database import get_db_context, close_db
    from db import crud
    from db.models import SessionStatus

    async with get_db_context() as db:
        logs, _ = await crud.list_audit_logs(db, tenant_id=tenant_id)
        updated_log = next(log for log in logs if log.id == log_id)
        check("Audit log xai_pending cleared", updated_log.xai_pending is False)
        check("Audit log xai_explanation backfilled", updated_log.xai_explanation == "This is a mocked XAI explanation.")

        db_session = await crud.get_session(db, session_id=session_id, tenant_id=tenant_id)
        check("Agent session marked COMPLETED", db_session.status == SessionStatus.COMPLETED)
        check("Agent session result recorded", db_session.result_summary == "Mocked agent execution completed.")

        db_cancel_session = await crud.get_session(db, session_id=cancel_session_id, tenant_id=tenant_id)
        check("Session marked CANCELLED in DB", db_cancel_session.status == SessionStatus.CANCELLED)
        
    await close_db()

def main():
    print("=" * 70)
    print(" ABSs v2.0 — Background Workers Verification (Component 4)")
    print("=" * 70)
    
    print("\n--- Initializing DB & Setup ---")
    tenant_id, session_id, log_id, cancel_session_id = asyncio.run(async_setup())
    
    sync_execute_tasks(tenant_id, session_id, log_id, cancel_session_id)
    
    print("\n--- Verifying Database State ---")
    asyncio.run(async_verify(tenant_id, session_id, log_id, cancel_session_id))
    
    print("\n--- Summary ---")
    print(f"Total passed: {passed}")
    print(f"Total failed: {failed}")
    
    if failed > 0:
        sys.exit(1)

def test_workers_pytest():
    main()

if __name__ == "__main__":
    main()
