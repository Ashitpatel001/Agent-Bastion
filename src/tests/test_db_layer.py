"""
tests/test_db_layer.py — Verification script for Component 1.

Run with:
    python -m pytest tests/test_db_layer.py -v

Or standalone:
    python tests/test_db_layer.py

This script validates:
  1. Database initialization (table creation).
  2. Tenant creation with API key hashing.
  3. Tenant lookup by raw API key.
  4. Default policy auto-creation on tenant registration.
  5. Policy CRUD with versioning (deactivate old, create new).
  6. Agent session lifecycle (QUEUED → RUNNING → COMPLETED).
  7. Audit log insertion and tenant-isolated queries.
  8. Cross-tenant isolation (Tenant A cannot see Tenant B data).
  9. Dashboard statistics aggregation.
"""

import asyncio
import os
import sys

# Ensure project root is on the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Force SQLite in-memory for testing — no files created.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
@pytest.mark.asyncio
async def test_db_layer_verification():
    await run_tests()


async def run_tests():
    from db.database import init_db, close_db, get_db_context
    from db import crud
    from db.models import SessionStatus
    from db.schemas import AuditLogCreate, PolicyCreate, PolicyUpdate

    print("=" * 70)
    print(" ABSs v2.0 — Database Layer Verification")
    print("=" * 70)
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ PASS: {name}")
            passed += 1
        else:
            print(f"  ❌ FAIL: {name} — {detail}")
            failed += 1

    # ------------------------------------------------------------------
    # Test 1: Database init
    # ------------------------------------------------------------------
    print("\n🔧 Test 1: Database Initialization")
    try:
        await init_db()
        check("Tables created", True)
    except Exception as e:
        check("Tables created", False, str(e))
        return

    # ------------------------------------------------------------------
    # Test 2: Tenant creation
    # ------------------------------------------------------------------
    print("\n👤 Test 2: Tenant Creation & API Key Hashing")
    async with get_db_context() as db:
        tenant_a, raw_key_a = await crud.create_tenant(
            db, name="Acme Corp", email="admin@acme.com"
        )
        check("Tenant A created", tenant_a.id is not None)
        check("API key starts with prefix", raw_key_a.startswith("abs_"))
        check("API key prefix stored", len(tenant_a.api_key_prefix) == 12)
        check("API key hash is SHA-256 (64 hex chars)", len(tenant_a.api_key_hash) == 64)
        check("Raw key != stored hash", raw_key_a != tenant_a.api_key_hash)

    # ------------------------------------------------------------------
    # Test 3: Tenant lookup by API key
    # ------------------------------------------------------------------
    print("\n🔑 Test 3: Tenant Lookup by API Key")
    async with get_db_context() as db:
        found = await crud.get_tenant_by_api_key(db, raw_key_a)
        check("Tenant found by raw API key", found is not None)
        check("Correct tenant returned", found and found.id == tenant_a.id)

        not_found = await crud.get_tenant_by_api_key(db, "abs_invalid_key_12345")
        check("Invalid key returns None", not_found is None)

    # ------------------------------------------------------------------
    # Test 4: Default policy auto-created
    # ------------------------------------------------------------------
    print("\n📋 Test 4: Default Policy Auto-Creation")
    async with get_db_context() as db:
        policy = await crud.get_active_policy(db, tenant_a.id)
        check("Default policy exists", policy is not None)
        check("Policy is active", policy and policy.is_active)
        check("Default blocked domains set", policy and len(policy.blocked_domains) > 0)
        check("Default DLP patterns set", policy and len(policy.blocked_input_patterns) > 0)
        check("Default risk tolerance = 75", policy and policy.max_risk_tolerance == 75)

    # ------------------------------------------------------------------
    # Test 5: Policy update & versioning
    # ------------------------------------------------------------------
    print("\n🔄 Test 5: Policy Update & Versioning")
    async with get_db_context() as db:
        old_policy = await crud.get_active_policy(db, tenant_a.id)
        old_policy_id = old_policy.id

        new_policy = await crud.create_policy(
            db,
            tenant_a.id,
            PolicyCreate(
                blocked_domains=["*.ru", "*.cn", "example-evil.com"],
                max_risk_tolerance=50,
            ),
        )
        check("New policy created", new_policy is not None)
        check("New policy is active", new_policy.is_active)
        check("New risk tolerance = 50", new_policy.max_risk_tolerance == 50)

    async with get_db_context() as db:
        active = await crud.get_active_policy(db, tenant_a.id)
        check("Active policy is the new one", active and active.id == new_policy.id)

    # Partial update
    async with get_db_context() as db:
        updated = await crud.update_policy(
            db, tenant_a.id, PolicyUpdate(max_risk_tolerance=60)
        )
        check("Partial update works", updated and updated.max_risk_tolerance == 60)
        check("Other fields unchanged", updated and len(updated.blocked_domains) == 3)

    # ------------------------------------------------------------------
    # Test 6: Agent session lifecycle
    # ------------------------------------------------------------------
    print("\n🤖 Test 6: Agent Session Lifecycle")
    async with get_db_context() as db:
        session = await crud.create_session(
            db,
            tenant_a.id,
            task_prompt="Go to amazon.com and search for laptops.",
            target_url="https://amazon.com",
        )
        check("Session created in QUEUED", session.status == SessionStatus.QUEUED)

    async with get_db_context() as db:
        session = await crud.update_session_status(
            db, session.id, tenant_a.id, SessionStatus.RUNNING
        )
        check("Session moved to RUNNING", session and session.status == SessionStatus.RUNNING)
        check("started_at populated", session and session.started_at is not None)

    async with get_db_context() as db:
        session = await crud.update_session_status(
            db, session.id, tenant_a.id, SessionStatus.COMPLETED,
            result_summary="Found 3 laptops under $1000."
        )
        check("Session COMPLETED", session and session.status == SessionStatus.COMPLETED)
        check("completed_at populated", session and session.completed_at is not None)
        check("Result summary saved", session and "3 laptops" in session.result_summary)

    # ------------------------------------------------------------------
    # Test 7: Audit log insertion
    # ------------------------------------------------------------------
    print("\n📝 Test 7: Audit Log Insertion")
    async with get_db_context() as db:
        log = await crud.create_audit_log(db, AuditLogCreate(
            tenant_id=tenant_a.id,
            session_id=session.id,
            event_type="INJECTION_ATTEMPT",
            url="http://evil.com",
            details="Blocked prompt injection: 'ignore previous instructions'",
            risk_level="CRITICAL",
            risk_score=95,
            action_taken="BLOCKED",
            xai_pending=True,
        ))
        check("Audit log created", log.id is not None)
        check("XAI pending flag set", log.xai_pending is True)

    # Backfill XAI
    async with get_db_context() as db:
        updated = await crud.update_audit_xai_explanation(
            db, log.id, "The agent tried to follow a malicious instruction."
        )
        check("XAI explanation backfilled", updated)

    # ------------------------------------------------------------------
    # Test 8: Cross-tenant isolation
    # ------------------------------------------------------------------
    print("\n🔒 Test 8: Cross-Tenant Data Isolation")
    async with get_db_context() as db:
        tenant_b, raw_key_b = await crud.create_tenant(
            db, name="Evil Corp", email="admin@evil.com"
        )

    # Tenant B should see zero sessions and zero audit logs.
    async with get_db_context() as db:
        b_sessions, b_total = await crud.list_sessions(db, tenant_b.id)
        check("Tenant B sees 0 sessions", b_total == 0)

        b_logs, b_log_total = await crud.list_audit_logs(db, tenant_b.id)
        check("Tenant B sees 0 audit logs", b_log_total == 0)

    # Tenant A should still see their data.
    async with get_db_context() as db:
        a_sessions, a_total = await crud.list_sessions(db, tenant_a.id)
        check("Tenant A sees 1 session", a_total == 1)

        a_logs, a_log_total = await crud.list_audit_logs(db, tenant_a.id)
        check("Tenant A sees 1 audit log", a_log_total == 1)

    # Tenant B cannot access Tenant A's session.
    async with get_db_context() as db:
        cross_session = await crud.get_session(db, session.id, tenant_b.id)
        check("Tenant B cannot access Tenant A session", cross_session is None)

    # ------------------------------------------------------------------
    # Test 9: Dashboard statistics
    # ------------------------------------------------------------------
    print("\n📊 Test 9: Dashboard Statistics Aggregation")
    async with get_db_context() as db:
        # Add more varied audit logs for stats.
        for i in range(5):
            await crud.create_audit_log(db, AuditLogCreate(
                tenant_id=tenant_a.id,
                event_type="RISK_ASSESSMENT",
                risk_level="LOW",
                risk_score=15 + i,
                action_taken="ALLOWED",
            ))
        await crud.create_audit_log(db, AuditLogCreate(
            tenant_id=tenant_a.id,
            event_type="CROSS_ORIGIN_BLOCKED",
            risk_level="HIGH",
            risk_score=88,
            action_taken="BLOCKED",
        ))

    async with get_db_context() as db:
        stats = await crud.get_audit_stats(db, tenant_a.id)
        check("Total events = 7", stats["total_events"] == 7)
        check("Risk distribution has CRITICAL", "CRITICAL" in stats["risk_distribution"])
        check("Average risk > 0", stats["average_risk_score"] > 0)
        check("Top event types populated", len(stats["top_event_types"]) > 0)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    await close_db()

    print("\n" + "=" * 70)
    print(f" Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)

    assert failed == 0, f"{failed} test checks failed in run_tests()"
    print("\n 🎉 Component 1 (Database & Multi-Tenant Data Layer) verified!\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
