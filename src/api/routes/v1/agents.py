from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional

from db.database import get_db
from db import crud, schemas
from api.auth import get_current_tenant
from db.models import Tenant, SessionStatus, TenantTier
from workers.agent_tasks import run_agent_task
from security.rate_limiter import require_rate_limit

router = APIRouter()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_rate_limit("worker"))])
async def submit_agent_task(
    request: schemas.AgentSessionCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Submit a new autonomous agent task with multi-tenant isolation and priority routing (Phase 4)."""
    # Determine target queue based on priority request or tenant tier
    queue_name = request.queue_name or "agents"
    priority = request.priority or 5
    if current_tenant.tier in [TenantTier.PRO, TenantTier.ENTERPRISE] and priority <= 3:
        queue_name = "priority_agents"

    session = await crud.create_session(
        db, 
        tenant_id=current_tenant.id,
        task_prompt=request.task_prompt,
        target_url=request.target_url,
        user_id=getattr(current_tenant, "user_id", None),
        queue_name=queue_name,
        priority=priority,
        max_retries=request.max_retries if request.max_retries is not None else 3,
    )
    await db.commit()
    
    # Enqueue task via resilient dispatcher with queue and priority support
    from workers.dispatch import dispatch_task
    dispatch_result = dispatch_task(
        run_agent_task, session.id, current_tenant.id,
        queue=queue_name, priority=priority
    )
    
    # Track celery task ID if available
    celery_task_id = getattr(dispatch_result, "id", None)
    if celery_task_id:
        await crud.update_session_status(
            db, session.id, current_tenant.id, SessionStatus.QUEUED,
            celery_task_id=celery_task_id
        )
        await db.commit()
    
    return {
        "session_id": session.id,
        "status": "QUEUED",
        "queue_name": queue_name,
        "priority": priority,
        "celery_task_id": celery_task_id
    }


@router.get("/workers/health", response_model=schemas.WorkerHealthResponse, dependencies=[Depends(require_rate_limit("worker"))])
async def get_worker_health(
    current_tenant: Tenant = Depends(get_current_tenant),
) -> Any:
    """Get real-time health and status of background Celery worker infrastructure (Task 9)."""
    from workers.celery_app import celery_app
    from workers.dispatch import is_redis_available
    
    if not is_redis_available():
        return schemas.WorkerHealthResponse(
            status="offline_fallback",
            active_workers=1,
            active_tasks=0,
            reserved_tasks=0,
            queues=["local_background_thread"],
            details={"broker": "redis_offline", "mode": "local_thread_fallback"}
        )
        
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        inspect = await loop.run_in_executor(None, lambda: celery_app.control.inspect(timeout=0.5))
        active = await loop.run_in_executor(None, lambda: inspect.active() if inspect else {})
        reserved = await loop.run_in_executor(None, lambda: inspect.reserved() if inspect else {})
        stats = await loop.run_in_executor(None, lambda: inspect.stats() if inspect else {})
        
        active_count = sum(len(tasks) for tasks in active.values())
        reserved_count = sum(len(tasks) for tasks in reserved.values())
        worker_count = len(stats)
        
        return schemas.WorkerHealthResponse(
            status="healthy" if worker_count > 0 else "degraded",
            active_workers=worker_count,
            active_tasks=active_count,
            reserved_tasks=reserved_count,
            queues=["agents", "priority_agents", "xai", "default"],
            details={"workers": list(stats.keys())}
        )
    except Exception as e:
        return schemas.WorkerHealthResponse(
            status="degraded",
            active_workers=0,
            active_tasks=0,
            reserved_tasks=0,
            queues=["agents", "xai"],
            details={"error": str(e)}
        )


@router.get("/queues/stats", response_model=schemas.QueueStatsResponse, dependencies=[Depends(require_rate_limit("worker"))])
async def get_queue_stats(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Gather real-time task queue statistics and lifecycle counts (Task 8 & 9)."""
    stats_data = await crud.get_queue_statistics(db, tenant_id=current_tenant.id)
    return schemas.QueueStatsResponse(**stats_data)


@router.get("", response_model=List[schemas.AgentSessionResponse], dependencies=[Depends(require_rate_limit("worker"))])
async def list_agent_sessions(
    status_filter: Optional[SessionStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List agent sessions for the current tenant with optional status filtering and pagination."""
    sessions, _ = await crud.list_sessions(
        db, current_tenant.id, status=status_filter, page=page, page_size=page_size
    )
    return sessions


@router.get("/{session_id}", response_model=schemas.AgentSessionResponse, dependencies=[Depends(require_rate_limit("worker"))])
async def get_agent_status(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get the status and explicit lifecycle transitions of an agent session."""
    session = await crud.get_session(db, session_id, current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/cancel", response_model=Dict[str, Any], dependencies=[Depends(require_rate_limit("worker"))])
async def cancel_agent_task(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Cancel a running agent task and actively revoke worker execution (Task 4.1 & Task 8)."""
    session = await crud.get_session(db, session_id, current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED, SessionStatus.TIMED_OUT]:
        raise HTTPException(status_code=400, detail="Cannot cancel a finished or timed out session")
        
    await crud.update_session_status(db, session_id, current_tenant.id, SessionStatus.CANCELLED, result_summary="Cancelled by user via API")
    await db.commit()

    try:
        from workers.agent_tasks import cancel_agent_task as cancel_worker_task
        from workers.dispatch import dispatch_task
        dispatch_task(cancel_worker_task, session_id, current_tenant.id, queue=session.queue_name)
    except Exception:
        pass
    
    return {"session_id": session_id, "status": "CANCELLED", "message": "Session marked as cancelled and worker termination signaled"}


@router.post("/{session_id}/retry", response_model=Dict[str, Any], dependencies=[Depends(require_rate_limit("worker"))])
async def retry_agent_task(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Retry a failed or timed out autonomous agent task (DX Layer - Phase 5)."""
    session = await crud.get_session(db, session_id, current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.status not in [SessionStatus.FAILED, SessionStatus.TIMED_OUT, SessionStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail=f"Cannot retry a session in state: {session.status.value}")
        
    await crud.update_session_status(
        db, session_id, current_tenant.id, SessionStatus.QUEUED,
        error_message=None
    )
    session.retry_count = (session.retry_count or 0) + 1
    await db.commit()
    
    from workers.dispatch import dispatch_task
    dispatch_result = dispatch_task(
        run_agent_task, session.id, current_tenant.id,
        queue=session.queue_name, priority=session.priority
    )
    
    celery_task_id = getattr(dispatch_result, "id", None)
    if celery_task_id:
        await crud.update_session_status(
            db, session.id, current_tenant.id, SessionStatus.QUEUED,
            celery_task_id=celery_task_id
        )
        await db.commit()
        
    return {
        "session_id": session.id,
        "status": "QUEUED",
        "retry_count": session.retry_count,
        "message": "Session requeued for execution",
        "celery_task_id": celery_task_id
    }
