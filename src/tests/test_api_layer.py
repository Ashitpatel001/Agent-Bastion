import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import asyncio
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from db.database import get_db
from db.models import Base

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
    # Setup tables
    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(init_tables())
    yield
    
    # Teardown tables
    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(drop_tables())
    app.dependency_overrides.clear()

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "abs-proxy-api"
    assert data["status"] in ["ok", "degraded"]
    assert "components" in data

def test_tenant_registration_and_api_key():
    # 1. Register a tenant
    response = client.post("/v1/tenants", json={
        "name": "Test Tenant",
        "email": "test@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert "raw_api_key" in data
    assert data["tenant"]["name"] == "Test Tenant"
    
    raw_api_key = data["raw_api_key"]
    
    # 2. Get active policy using the raw API key
    headers = {"X-API-Key": raw_api_key}
    policy_response = client.get("/v1/security/policies", headers=headers)
    assert policy_response.status_code == 200
    assert policy_response.json()["max_risk_tolerance"] == 75

def test_agent_task_submission():
    # Register tenant to get API key
    res = client.post("/v1/tenants", json={"name": "Agent Tenant", "email": "agent@example.com"})
    raw_api_key = res.json()["raw_api_key"]
    headers = {"X-API-Key": raw_api_key}
    
    # Submit task
    task_res = client.post("/v1/agent/run", headers=headers, json={
        "task_prompt": "Search for news",
        "target_url": "https://news.ycombinator.com"
    })
    assert task_res.status_code == 201
    task_data = task_res.json()
    assert task_data["status"] == "QUEUED"
    job_id = task_data["id"]
    
    # Check status
    status_res = client.get(f"/v1/agent/status/{job_id}", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "QUEUED"

def test_security_logs_endpoint():
    res = client.post("/v1/tenants", json={"name": "Sec Tenant", "email": "sec@example.com"})
    headers = {"X-API-Key": res.json()["raw_api_key"]}
    
    logs_res = client.get("/v1/security/logs", headers=headers)
    assert logs_res.status_code == 200
    assert logs_res.json()["total"] == 0

def test_unauthorized_access():
    response = client.get("/v1/security/policies")
    assert response.status_code == 401

    headers = {"X-API-Key": "invalid_key"}
    response = client.get("/v1/security/policies", headers=headers)
    assert response.status_code == 401
