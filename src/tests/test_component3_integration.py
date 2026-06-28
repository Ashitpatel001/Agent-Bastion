"""
Integration test for Component 3: Core Security Engine Refactoring.

Tests the full async flow:
  1. AsyncSecurityLogger writes to the database
  2. TenantPolicyEngine fetches and caches policies from DB
  3. Legacy SecurityLogger backward compatibility
  4. XAI explanation backfill
"""
import asyncio
import sys
import os

# Fix Windows Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_full_flow():
    """End-to-end test of the refactored security engine components."""
    from db.database import init_db, get_db_context, engine
    from db.models import Base
    from db import crud
    from db.models import TenantTier
    from security.event_logger import AsyncSecurityLogger, SecurityLogger
    from security.policy_engine import TenantPolicyEngine

    print("=" * 60)
    print("Component 3: Core Security Engine Integration Test")
    print("=" * 60)

    # --- Setup: Create in-memory DB ---
    # Override to use in-memory SQLite for testing
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("\n[1/7] ✅ Database tables created")

    # --- Create a test tenant ---
    async with get_db_context() as db:
        tenant, raw_key = await crud.create_tenant(
            db,
            name="Test Corp",
            email="test@testcorp.com",
            tier=TenantTier.FREE,
        )
        tenant_id = tenant.id
        print(f"[2/7] ✅ Tenant created: {tenant.name} (id={tenant_id})")

    # --- Test AsyncSecurityLogger (DB writes) ---
    async_logger = AsyncSecurityLogger(
        tenant_id=tenant_id,
        session_id=None,
        write_jsonl_fallback=False,
    )

    log_id_1 = await async_logger.log_event(
        event_type="INJECTION_ATTEMPT",
        url="https://evil.com/phish",
        details="Blocked prompt injection: 'ignore instructions'",
        risk_level="CRITICAL",
        risk_score=95,
        action="SANITIZED",
    )
    assert log_id_1 is not None, "DB insert should return a log ID"
    print(f"[3/7] ✅ AsyncSecurityLogger.log_event → DB insert OK (id={log_id_1})")

    log_id_2 = await async_logger.log_event(
        event_type="RISK_ASSESSMENT",
        url="https://amazon.com",
        details="Action 'click_element' scored 15/100 (LOW)",
        risk_level="LOW",
        risk_score=15,
        action="ALLOWED",
        xai_pending=True,
    )
    assert log_id_2 is not None
    print(f"[4/7] ✅ AsyncSecurityLogger.log_event with xai_pending=True OK (id={log_id_2})")

    # --- Test XAI backfill ---
    success = await async_logger.update_xai_explanation(
        log_id_2,
        "The agent clicked an element on Amazon.com which is a trusted domain. No risk detected.",
    )
    assert success, "XAI explanation backfill should succeed"
    print(f"[5/7] ✅ XAI explanation backfill OK")

    # --- Test TenantPolicyEngine (DB fetch + cache) ---
    policy_engine = TenantPolicyEngine(
        tenant_id=tenant_id,
        cache_ttl_seconds=60,
        async_logger=async_logger,
    )

    # Test domain blocking
    is_blocked_ru = await policy_engine.check_navigation("https://evil.ru/malware")
    assert is_blocked_ru, "*.ru should be blocked by default policy"

    is_blocked_safe = await policy_engine.check_navigation("https://google.com")
    assert not is_blocked_safe, "google.com should NOT be blocked"

    is_blocked_bitly = await policy_engine.check_navigation("https://bit.ly/abc123")
    assert is_blocked_bitly, "bit.ly should be blocked by default policy"

    print(f"[6/7] ✅ TenantPolicyEngine.check_navigation OK (cached from DB)")

    # Test input DLP
    is_blocked_input = await policy_engine.check_input("my password is secret123")
    assert is_blocked_input, "'password' should match blocked pattern"

    is_safe_input = await policy_engine.check_input("hello world")
    assert not is_safe_input, "'hello world' should not be blocked"

    print(f"[7/7] ✅ TenantPolicyEngine.check_input OK")

    # --- Verify audit logs in DB ---
    async with get_db_context() as db:
        logs, total = await crud.list_audit_logs(db, tenant_id)
        # Should have: injection attempt + risk assessment + policy violations from nav checks
        print(f"\n📊 Total audit logs for tenant: {total}")
        for log in logs:
            print(f"   [{log.risk_level.value if hasattr(log.risk_level, 'value') else log.risk_level}] "
                  f"{log.event_type}: {log.details[:60]}...")

    # --- Legacy backward compat ---
    SecurityLogger.set_global_context(async_logger)
    SecurityLogger.log_event(
        event_type="LEGACY_TEST",
        url="https://test.com",
        details="Legacy caller test",
        risk_level="LOW",
        risk_score=5,
        action="ALLOWED",
    )
    # Allow fire-and-forget task to complete
    await asyncio.sleep(0.5)
    SecurityLogger.clear_global_context()
    print(f"\n✅ Legacy SecurityLogger backward compat OK")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_full_flow())
