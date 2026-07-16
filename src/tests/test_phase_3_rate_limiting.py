"""
tests/test_phase_3_rate_limiting.py — Complete Verification Suite for Phase 3 (Rate Limiting & Abuse Prevention).

Verifies:
  1. Redis / In-Memory sliding window rate limiting algorithm (Task 3.1 & 3.5).
  2. Per-endpoint limits (Auth: 10/min, Session create: 5/min, Tenant create: 2/hr, Default: 200/min) (Task 3.2).
  3. Per-tenant limits & policy override (`TenantPolicy.rate_limits`) taking the more restrictive quota (Task 3.3).
  4. RFC-compliant response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`) on success and 429 (Task 3.4).
  5. Multi-dimensional burst vs sustained window protection.
  6. Graceful offline / test mode fallback to in-memory sliding window sorted sets (`ZSET`).
"""

import pytest
import time
import uuid
import math
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.main import app
from api.config import settings
from security.rate_limiter import rate_limiter_engine, determine_endpoint_tier, get_redis_client
from db import crud, schemas, models
from db.database import get_db_context

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter_state():
    """Reset rate limiter state and verify DB tables exist before and after each test method."""
    import asyncio
    from db.database import init_db
    asyncio.run(init_db())
    asyncio.run(rate_limiter_engine.clear_all())
    yield
    asyncio.run(rate_limiter_engine.clear_all())


def test_endpoint_tier_classification():
    """Verify endpoint categorization and window assignment (Task 3.2)."""
    # Auth route
    tier, limit, window = determine_endpoint_tier("/api/v1/auth/login", "POST")
    assert tier == "auth"
    assert limit == settings.LOGIN_RATE_LIMIT
    assert window == settings.LOGIN_RATE_WINDOW

    # Worker session create route
    tier, limit, window = determine_endpoint_tier("/api/v1/agents/session", "POST")
    assert tier == "worker"
    assert limit == settings.WORKER_LIMIT
    assert window == settings.WORKER_RATE_WINDOW

    # Tenant create route
    tier, limit, window = determine_endpoint_tier("/api/v1/tenants", "POST")
    assert tier == "tenant_create"
    assert limit == settings.TENANT_CREATE_LIMIT
    assert window == settings.TENANT_CREATE_WINDOW

    # Default route
    tier, limit, window = determine_endpoint_tier("/api/v1/some-random-endpoint", "GET")
    assert tier == "default"
    assert limit == settings.DEFAULT_RATE_LIMIT
    assert window == settings.DEFAULT_RATE_WINDOW


def test_rate_limiter_middleware_headers_on_success():
    """Verify that successful requests include RFC-compliant rate limit response headers (Task 3.4)."""
    headers = {
        "X-Test-Rate-Limit": "true",
        "X-Forwarded-For": f"192.168.10.{uuid.uuid4().hex[:4]}"
    }
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    # For health / public endpoints, remaining should be strictly numeric and non-negative
    rem = int(response.headers["X-RateLimit-Remaining"])
    assert rem >= 0


def test_auth_endpoint_rate_limit_and_429_headers():
    """
    Verify Auth endpoint rate limit (Task 3.2: 10/min).
    Ensures that hitting login 10 times decrements X-RateLimit-Remaining down to 0,
    and the 11th request triggers exact HTTP 429 Too Many Requests with Retry-After header.
    """
    test_ip = f"10.0.1.{uuid.uuid4().hex[:4]}"
    headers = {
        "X-Test-Rate-Limit": "true",
        "X-Forwarded-For": test_ip,
        "Content-Type": "application/json"
    }
    payload = {"email": "invalid_user@abss.internal", "password": "wrong_password"}

    # Execute up to the limit (10 requests)
    for i in range(settings.LOGIN_RATE_LIMIT):
        res = client.post("/api/v1/auth/login", json=payload, headers=headers)
        # Even if login fails with 401, rate limiter tracks the request
        assert res.status_code in (200, 401, 403, 404, 422), f"Unexpected status {res.status_code}"
        assert "X-RateLimit-Remaining" in res.headers
        expected_rem = max(0, settings.LOGIN_RATE_LIMIT - (i + 1))
        assert int(res.headers["X-RateLimit-Remaining"]) == expected_rem

    # 11th request must be blocked by rate limiting middleware with HTTP 429
    res_429 = client.post("/api/v1/auth/login", json=payload, headers=headers)
    assert res_429.status_code == 429
    assert "Retry-After" in res_429.headers
    assert "X-RateLimit-Limit" in res_429.headers
    assert int(res_429.headers["X-RateLimit-Remaining"]) == 0

    data = res_429.json()
    assert "error" in data
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after" in data["error"]["details"]


def test_worker_session_create_rate_limit():
    """
    Verify Session/Worker creation rate limit (Task 3.2: 5/min).
    """
    test_ip = f"10.0.2.{uuid.uuid4().hex[:4]}"
    headers = {
        "X-Test-Rate-Limit": "true",
        "X-Forwarded-For": test_ip,
        "Content-Type": "application/json"
    }
    payload = {"tenant_id": "dummy_tenant", "task_prompt": "Run security check"}

    for _ in range(settings.WORKER_LIMIT):
        res = client.post("/api/v1/agents/session", json=payload, headers=headers)
        assert res.status_code != 429

    # 6th request triggers 429
    res_blocked = client.post("/api/v1/agents/session", json=payload, headers=headers)
    assert res_blocked.status_code == 429
    assert "Retry-After" in res_blocked.headers
    assert res_blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_tenant_create_rate_limit():
    """
    Verify Tenant creation rate limit (Task 3.2: 2/hr).
    """
    test_ip = f"10.0.3.{uuid.uuid4().hex[:4]}"
    headers = {
        "X-Test-Rate-Limit": "true",
        "X-Forwarded-For": test_ip,
        "Content-Type": "application/json"
    }

    for i in range(settings.TENANT_CREATE_LIMIT):
        payload = {"name": f"Test Tenant {i}", "email": f"t_{i}_{uuid.uuid4().hex[:4]}@test.internal"}
        res = client.post("/api/v1/tenants", json=payload, headers=headers)
        assert res.status_code != 429

    # 3rd request inside the 1-hour window must be blocked with HTTP 429
    payload = {"name": "Test Tenant Blocked", "email": f"t_blocked_{uuid.uuid4().hex[:4]}@test.internal"}
    res_blocked = client.post("/api/v1/tenants", json=payload, headers=headers)
    assert res_blocked.status_code == 429
    assert "Retry-After" in res_blocked.headers


@pytest.mark.asyncio
async def test_per_tenant_quota_and_restrictive_override():
    """
    Verify per-tenant rate limits from TenantPolicy.rate_limits (Task 3.3).
    Ensures that when a tenant has a custom quota (e.g. 3 requests/min),
    the policy engine enforces the more restrictive limit of IP vs Tenant limit.
    """
    import jwt
    from security.config import SecurityConfig

    # Create test tenant and set restrictive policy
    async with get_db_context() as db:
        tenant, _ = await crud.create_tenant(
            db,
            name="Quota Tenant",
            email=f"quota_{uuid.uuid4().hex[:6]}@test.internal",
            tier=models.TenantTier.FREE
        )
        tenant_id = tenant.id

        # Update active policy with a very strict quota (3 requests / minute)
        policy_update = schemas.PolicyUpdate(
            rate_limits={"requests_per_minute": 3, "burst_limit": 3}
        )
        await crud.update_policy(db, tenant_id, policy_update)
        await db.commit()

    from security.policy_engine import TenantPolicyEngine
    TenantPolicyEngine(tenant_id)._cached_policy = None

    # Generate valid JWT containing tenant_id
    payload = {
        "sub": "user_quota_test",
        "tenant_id": tenant_id,
        "role": models.UserRole.DEVELOPER.value,
        "exp": time.time() + 3600
    }
    token = jwt.encode(payload, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)

    headers = {
        "X-Test-Rate-Limit": "true",
        "X-Forwarded-For": f"10.0.4.{uuid.uuid4().hex[:4]}",
        "Authorization": f"Bearer {token}"
    }

    # First 3 requests allowed under tenant quota
    for _ in range(3):
        res = client.get(f"/api/v1/tenants/{tenant_id}/policy", headers=headers)
        assert res.status_code != 429

    # 4th request must be blocked because tenant quota (3/min) < IP default limit (200/min)
    res_blocked = client.get(f"/api/v1/tenants/{tenant_id}/policy", headers=headers)
    assert res_blocked.status_code == 429
    assert res_blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Tenant rate quota exceeded" in res_blocked.json()["error"]["message"]


@pytest.mark.asyncio
async def test_sliding_window_expiration_and_recovery():
    """
    Verify sliding window counter sorted set (`ZSET`) trimming.
    Ensures that once timestamp entries fall outside the window, capacity is restored.
    """
    key = f"rl:test:window:{uuid.uuid4().hex[:6]}"
    limit = 2
    window_seconds = 1

    # First 2 checks pass
    allowed1, rem1, _ = await rate_limiter_engine.check_window(key, limit, window_seconds)
    assert allowed1 is True
    assert rem1 == 1

    allowed2, rem2, _ = await rate_limiter_engine.check_window(key, limit, window_seconds)
    assert allowed2 is True
    assert rem2 == 0

    # 3rd check exceeds limit
    allowed3, rem3, retry_after = await rate_limiter_engine.check_window(key, limit, window_seconds)
    assert allowed3 is False
    assert rem3 == 0
    assert retry_after > 0

    # Wait for sliding window to advance past 1 second
    import asyncio
    await asyncio.sleep(1.1)

    # Window expired -> capacity restored
    allowed4, rem4, _ = await rate_limiter_engine.check_window(key, limit, window_seconds)
    assert allowed4 is True
    assert rem4 == 1


@pytest.mark.asyncio
async def test_api_key_rate_limiting():
    """Verify per-API-key rate limiting dimension."""
    test_ip = f"10.0.5.{uuid.uuid4().hex[:4]}"
    api_key = f"sk-test-apikey-{uuid.uuid4().hex}"
    headers = {
        "X-Test-Rate-Limit": "true",
        "X-Forwarded-For": test_ip,
        "X-API-Key": api_key
    }

    import hashlib
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
    rl_key = f"rl:apikey:{key_hash}"

    for _ in range(settings.API_KEY_LIMIT):
        await rate_limiter_engine.check_window(rl_key, settings.API_KEY_LIMIT, settings.API_KEY_WINDOW)

    # Next HTTP request with this exact API key should get blocked
    res = client.get("/api/v1/system/health", headers=headers)
    assert res.status_code == 429
    assert "API key rate limit exceeded" in res.json()["error"]["message"]
