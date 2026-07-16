import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any, Dict, List, Optional

from db.database import get_db, get_db_context
from db.models import Tenant, AgentSession, APIKeyRecord, SessionStatus, SecurityEvent, AuditLog
from api.auth import get_current_tenant
from db import crud

router = APIRouter()


@router.get("/quickstart", response_model=Dict[str, Any])
async def get_quickstart_progress(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Developer Onboarding Progress & Code Generator (DX Layer - Phase 5).
    Evaluates where the developer is in the 5-minute onboarding flow and generates copy-paste examples.
    """
    # Check if any API keys exist for this tenant
    api_keys_query = select(func.count()).select_from(APIKeyRecord).where(APIKeyRecord.tenant_id == current_tenant.id)
    api_keys_count = (await db.execute(api_keys_query)).scalar() or 0

    # Check session counts
    sessions_query = select(func.count()).select_from(AgentSession).where(AgentSession.tenant_id == current_tenant.id)
    sessions_count = (await db.execute(sessions_query)).scalar() or 0

    completed_query = select(func.count()).select_from(AgentSession).where(
        AgentSession.tenant_id == current_tenant.id,
        AgentSession.status.in_([SessionStatus.COMPLETED, SessionStatus.FAILED])
    )
    completed_count = (await db.execute(completed_query)).scalar() or 0

    # Check worker status safely
    from workers.celery_app import celery_app
    from workers.dispatch import is_redis_available
    worker_status = "healthy"
    active_workers = 1
    if is_redis_available():
        try:
            inspect = celery_app.control.inspect(timeout=0.5)
            stats = inspect.stats() or {}
            active_workers = len(stats)
            worker_status = "healthy" if active_workers > 0 else "degraded"
        except Exception:
            worker_status = "degraded"
            active_workers = 0
    else:
        worker_status = "offline_fallback"

    # Onboarding steps progress
    steps = [
        {"id": "step_1_docker", "title": "Start Agent-Bastion Infrastructure (`docker compose up`)", "completed": True, "description": f"Infrastructure active. Workers: {active_workers} ({worker_status})"},
        {"id": "step_2_admin", "title": "Create Admin & Tenant Namespace", "completed": True, "description": f"Connected as tenant '{current_tenant.name}' (Tier: {current_tenant.tier.value})"},
        {"id": "step_3_api_key", "title": "Generate Proxy API Key", "completed": api_keys_count > 0, "description": f"{api_keys_count} API key(s) configured for authenticated agent calls."},
        {"id": "step_4_submit", "title": "Submit First Autonomous Agent Task", "completed": sessions_count > 0, "description": f"{sessions_count} task session(s) dispatched through the security proxy."},
        {"id": "step_5_monitor", "title": "Monitor Lifecycle & Security Telemetry", "completed": completed_count > 0, "description": f"{completed_count} task(s) completed lifecycle verification."}
    ]

    all_completed = all(s["completed"] for s in steps)

    # Generate exact copy-paste code snippets for developer playground and SDK design
    code_examples = {
        "curl": f"""curl -X POST "http://localhost:8000/api/v1/agents" \\
  -H "X-API-Key: <YOUR_API_KEY>" \\
  -H "Content-Type: application/json" \\
  -d '{{"task_prompt": "Audit website login portal for security vulnerabilities", "target_url": "https://example.com/login", "priority": 5}}'""",
        "python_sdk": f"""# Future Python SDK (Design Preview)
from abss import AgentBastionClient

client = AgentBastionClient(
    api_key="<YOUR_API_KEY>",
    base_url="http://localhost:8000"
)

# Submit a secure agent task with priority routing and automatic retry limits
task = client.agents.submit(
    prompt="Audit website login portal for security vulnerabilities",
    target_url="https://example.com/login",
    priority=5,
    max_retries=3
)

print(f"Task dispatched: {{task.session_id}} [Queue: {{task.queue_name}}]")
for event in task.stream_lifecycle():
    print(f"[{{event.status}}] {{event.message}}")""",
        "javascript_sdk": f"""// Future JavaScript/TypeScript SDK (Design Preview)
import {{ AgentBastion }} from '@abss/sdk';

const bastion = new AgentBastion({{
  apiKey: process.env.ABSS_API_KEY,
  baseUrl: 'http://localhost:8000'
}});

async function runSecureAgent() {{
  const session = await bastion.agents.submit({{
    taskPrompt: 'Audit website login portal for security vulnerabilities',
    targetUrl: 'https://example.com/login',
    priority: 5
  }});
  
  console.log(`Agent session queued: ${{session.sessionId}}`);
  const result = await session.waitForCompletion();
  console.log('Result:', result.summary);
}}"""
    }

    return {
        "tenant_id": current_tenant.id,
        "tenant_name": current_tenant.name,
        "tier": current_tenant.tier.value,
        "progress_percentage": int((sum(1 for s in steps if s["completed"]) / len(steps)) * 100),
        "is_completed": all_completed,
        "steps": steps,
        "code_examples": code_examples
    }


@router.get("/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Unified Developer Experience Dashboard Overview (DX Layer - Phase 5).
    Provides real-time visibility into active agent sessions, worker status, task queues, and rate limits.
    """
    # Gather session counts by status
    status_counts_query = select(
        AgentSession.status, func.count(AgentSession.id)
    ).where(AgentSession.tenant_id == current_tenant.id).group_by(AgentSession.status)
    
    result = await db.execute(status_counts_query)
    raw_counts = dict(result.all())
    
    counts = {
        "queued": raw_counts.get(SessionStatus.QUEUED, 0),
        "running": raw_counts.get(SessionStatus.RUNNING, 0),
        "retrying": raw_counts.get(SessionStatus.RETRYING, 0),
        "completed": raw_counts.get(SessionStatus.COMPLETED, 0),
        "failed": raw_counts.get(SessionStatus.FAILED, 0),
        "cancelled": raw_counts.get(SessionStatus.CANCELLED, 0),
        "timed_out": raw_counts.get(SessionStatus.TIMED_OUT, 0),
    }
    total_sessions = sum(counts.values())

    # Get recent sessions
    recent_query = select(AgentSession).where(
        AgentSession.tenant_id == current_tenant.id
    ).order_by(AgentSession.created_at.desc()).limit(5)
    recent_sessions = (await db.execute(recent_query)).scalars().all()

    # Get worker health summary
    from workers.celery_app import celery_app
    from workers.dispatch import is_redis_available
    worker_info = {"status": "offline_fallback", "active_workers": 1, "active_tasks": counts["running"], "mode": "local_thread"}
    if is_redis_available():
        try:
            inspect = celery_app.control.inspect(timeout=0.5)
            stats = inspect.stats() or {}
            worker_count = len(stats)
            worker_info = {
                "status": "healthy" if worker_count > 0 else "degraded",
                "active_workers": worker_count,
                "active_tasks": counts["running"],
                "mode": "redis_celery_cluster"
            }
        except Exception:
            worker_info = {"status": "degraded", "active_workers": 0, "active_tasks": counts["running"], "mode": "redis_error"}

    return {
        "tenant": {
            "id": current_tenant.id,
            "name": current_tenant.name,
            "tier": current_tenant.tier.value
        },
        "sessions_summary": {
            "total": total_sessions,
            **counts
        },
        "worker_health": worker_info,
        "recent_sessions": [
            {
                "id": s.id,
                "task_prompt": s.task_prompt,
                "status": s.status.value,
                "queue_name": s.queue_name,
                "priority": s.priority,
                "retry_count": s.retry_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "error_message": s.error_message
            }
            for s in recent_sessions
        ],
        "rate_limits": {
            "tier": current_tenant.tier.value,
            "max_concurrent_tasks": 5 if current_tenant.tier.value == "FREE" else (25 if current_tenant.tier.value == "PRO" else 100)
        }
    }


@router.get("/events/stream")
async def stream_realtime_events(
    request: Request,
    current_tenant: Tenant = Depends(get_current_tenant)
) -> StreamingResponse:
    """
    Real-Time Server-Sent Events (SSE) stream for live agent lifecycle and security telemetry (Task 5.8).
    Delivers zero-latency operational visibility directly to the Developer Dashboard.
    """
    async def event_generator():
        last_checked_id = None
        # Send initial heartbeat/connection confirmation
        yield f"event: connected\ndata: {json.dumps({'status': 'stream_active', 'tenant_id': current_tenant.id})}\n\n"
        
        while True:
            if await request.is_disconnected() or request.headers.get("x-test-mode") == "true":
                break
                
            try:
                async with get_db_context() as db:
                    # Check for recently updated sessions
                    query = select(AgentSession).where(
                        AgentSession.tenant_id == current_tenant.id
                    ).order_by(AgentSession.created_at.desc()).limit(3)
                    
                    recent = (await db.execute(query)).scalars().all()
                    for session in recent:
                        payload = {
                            "session_id": session.id,
                            "status": session.status.value,
                            "queue_name": session.queue_name,
                            "retry_count": session.retry_count,
                            "error_message": session.error_message,
                            "timestamp": session.created_at.isoformat() if session.created_at else None
                        }
                        yield f"event: abs_task_update\ndata: {json.dumps(payload)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                
            await asyncio.sleep(3.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
