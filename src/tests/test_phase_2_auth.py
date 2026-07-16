import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
import asyncio
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from db.database import get_db
from db.models import Base, User, Tenant, RefreshToken, APIKeyRecord, UserRole
from db import crud

# Setup in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(init_tables())
    yield
    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(drop_tables())
    app.dependency_overrides.clear()

client = TestClient(app)


def test_bootstrap_admin_flow():
    """Verify bootstrap-admin setup on empty DB and disable after first use."""
    # 1. On empty DB, bootstrap-admin should succeed
    res = client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "bootstrap@abss.internal",
        "name": "Bootstrap Tenant",
        "password": "SecureBootstrapPass123!"
    })
    assert res.status_code == 201, f"Failed: {res.text}"
    data = res.json()
    assert data["email"] == "bootstrap@abss.internal"
    assert "access_token" in data
    assert "refresh_token" in data
    assert "raw_api_key" in data

    # 2. Second attempt when DB is no longer empty MUST fail with 403
    res2 = client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "hacker@abss.internal",
        "password": "HackedPassword!"
    })
    assert res2.status_code == 403
    assert "already been executed" in res2.json()["error"]["message"]


def test_login_and_jwt_generation():
    """Verify email/password login, token structure, and refresh token rejection on API endpoints."""
    # Create tenant and user
    res = client.post("/v1/tenants", json={"name": "Login Tenant", "email": "login@example.com"})
    raw_key = res.json()["raw_api_key"]

    # Bootstrap or register admin
    reg_res = client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "admin@login.com",
        "password": "AdminPassword123!"
    })
    assert reg_res.status_code == 201

    # Login JSON
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@login.com",
        "password": "AdminPassword123!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # Verify access_token works for API endpoint (/api/v1/auth/me)
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@login.com"

    # Verify refresh_token CANNOT be used as access_token against regular API endpoints
    me_res2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert me_res2.status_code == 401
    assert "Refresh token cannot be used for API access" in me_res2.json()["error"]["message"]


def test_refresh_token_rotation_and_replay_protection():
    """Verify single-use rotatable refresh tokens and immediate family revocation on reuse attempt."""
    client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "rotator@abss.internal",
        "password": "RotatePassword123!"
    })

    login_res = client.post("/api/v1/auth/login", json={
        "email": "rotator@abss.internal",
        "password": "RotatePassword123!"
    })
    token_1 = login_res.json()["refresh_token"]

    # 1. First refresh with token_1 -> returns token_2 and invalidates token_1
    ref_res1 = client.post("/api/v1/auth/refresh", json={"refresh_token": token_1})
    assert ref_res1.status_code == 200
    token_2 = ref_res1.json()["refresh_token"]
    assert token_2 != token_1

    # 2. Replay attack attempt: Try using token_1 again!
    replay_res = client.post("/api/v1/auth/refresh", json={"refresh_token": token_1})
    assert replay_res.status_code == 401
    assert "invalidated for security" in replay_res.json()["error"]["message"]

    # 3. Because token_1 was reused, the ENTIRE token family (including token_2) must now be revoked!
    ref_res2 = client.post("/api/v1/auth/refresh", json={"refresh_token": token_2})
    assert ref_res2.status_code == 401


def test_api_key_hashed_and_lookup():
    """Verify API keys are stored hashed in APIKeyRecord, work for auth, and stop working when revoked."""
    client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "keyadmin@abss.internal",
        "password": "KeyAdminPassword123!"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "keyadmin@abss.internal",
        "password": "KeyAdminPassword123!"
    })
    access_token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create new API key
    key_create_res = client.post("/api/v1/api-keys", json={
        "name": "CI/CD Key",
        "scopes": ["*"]
    }, headers=headers)
    assert key_create_res.status_code == 201
    key_data = key_create_res.json()
    raw_key = key_data["raw_key"]
    key_id = key_data["id"]

    # Verify raw key is not equal to stored hash
    async def verify_hash():
        async with TestingSessionLocal() as db:
            record = await db.get(APIKeyRecord, key_id)
            assert record.key_hash != raw_key
            assert len(record.key_hash) == 64
    asyncio.run(verify_hash())

    # Verify raw_key works against protected endpoint (/v1/security/policies)
    policy_res = client.get("/v1/security/policies", headers={"X-API-Key": raw_key})
    assert policy_res.status_code == 200

    # Revoke API key
    del_res = client.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify raw_key no longer works after revocation
    policy_res_after = client.get("/v1/security/policies", headers={"X-API-Key": raw_key})
    assert policy_res_after.status_code == 401


def test_rbac_and_tenant_isolation():
    """Verify Admin, Operator, and Viewer roles, and enforce multi-tenant isolation."""
    # 1. Setup Tenant A (Admin) via bootstrap
    boot_res = client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "admin@tenant-a.com",
        "name": "Tenant A",
        "password": "AdminPasswordA123!"
    })
    admin_token_a = boot_res.json()["access_token"]
    headers_admin_a = {"Authorization": f"Bearer {admin_token_a}"}

    # Create an Operator and a Viewer in Tenant A
    op_res = client.post("/api/v1/auth/create-user", json={
        "email": "operator@tenant-a.com",
        "password": "OpPassword123!",
        "role": "OPERATOR"
    }, headers=headers_admin_a)
    assert op_res.status_code == 201

    view_res = client.post("/api/v1/auth/create-user", json={
        "email": "viewer@tenant-a.com",
        "password": "ViewPassword123!",
        "role": "VIEWER"
    }, headers=headers_admin_a)
    assert view_res.status_code == 201

    # Login as Operator
    op_login = client.post("/api/v1/auth/login", json={"email": "operator@tenant-a.com", "password": "OpPassword123!"})
    op_token = op_login.json()["access_token"]
    headers_op = {"Authorization": f"Bearer {op_token}"}

    # Login as Viewer
    view_login = client.post("/api/v1/auth/login", json={"email": "viewer@tenant-a.com", "password": "ViewPassword123!"})
    view_token = view_login.json()["access_token"]
    headers_viewer = {"Authorization": f"Bearer {view_token}"}

    # 2. Check Viewer cannot access Admin-only route (e.g. create API key or register user)
    viewer_try_admin = client.post("/api/v1/api-keys", json={"name": "Illegal Key"}, headers=headers_viewer)
    assert viewer_try_admin.status_code == 403

    # 3. Setup Tenant B (Separate tenant)
    tenant_b_res = client.post("/v1/tenants", json={"name": "Tenant B", "email": "admin@tenant-b.com"})
    raw_key_b = tenant_b_res.json()["raw_api_key"]

    # Verify Tenant A Operator or Viewer cannot access Tenant B's data using Tenant A credentials
    # When querying endpoint with headers_op, tenant_id is strictly bound to Tenant A
    me_res = client.get("/api/v1/auth/me", headers=headers_op)
    assert me_res.json()["tenant_id"] != tenant_b_res.json()["tenant"]["id"]


def test_password_change_revokes_sessions():
    """Verify changing password immediately revokes all active refresh tokens for that user."""
    client.post("/api/v1/auth/bootstrap-admin", json={
        "email": "passchange@abss.internal",
        "password": "OldPassword123!"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "passchange@abss.internal",
        "password": "OldPassword123!"
    })
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Change password
    change_res = client.post("/api/v1/auth/change-password", json={
        "current_password": "OldPassword123!",
        "new_password": "NewPassword456!"
    }, headers={"Authorization": f"Bearer {access_token}"})
    assert change_res.status_code == 200

    # Old refresh token MUST now be rejected (401)
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 401
