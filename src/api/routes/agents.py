import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from api.auth import get_current_tenant
from db.database import get_db
from db import crud, schemas
from db.models import Tenant, SessionStatus, TenantTier
from db.schemas import AgentSessionCreate, AgentSessionResponse, WorkerHealthResponse, QueueStatsResponse

logger = logging.getLogger("api.routes.agents")

router = APIRouter(prefix="/v1/agent", tags=["Agent Tasks"])


@router.get("/workers/health", response_model=WorkerHealthResponse)
async def get_legacy_worker_health(
    tenant: Tenant = Depends(get_current_tenant),
):
    """Get real-time health and status of background Celery worker infrastructure."""
    from workers.celery_app import celery_app
    from workers.dispatch import is_redis_available
    
    if not is_redis_available():
        return WorkerHealthResponse(
            status="offline_fallback",
            active_workers=1,
            active_tasks=0,
            reserved_tasks=0,
            queues=["local_background_thread"],
            details={"broker": "redis_offline", "mode": "local_thread_fallback"}
        )
        
    try:
        inspect = celery_app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        reserved = inspect.reserved() or {}
        stats = inspect.stats() or {}
        
        active_count = sum(len(tasks) for tasks in active.values())
        reserved_count = sum(len(tasks) for tasks in reserved.values())
        worker_count = len(stats)
        
        return WorkerHealthResponse(
            status="healthy" if worker_count > 0 else "degraded",
            active_workers=worker_count,
            active_tasks=active_count,
            reserved_tasks=reserved_count,
            queues=["agents", "priority_agents", "xai", "default"],
            details={"workers": list(stats.keys())}
        )
    except Exception as e:
        return WorkerHealthResponse(
            status="degraded",
            active_workers=0,
            active_tasks=0,
            reserved_tasks=0,
            queues=["agents", "xai"],
            details={"error": str(e)}
        )


@router.get("/queues/stats", response_model=QueueStatsResponse)
async def get_legacy_queue_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Gather real-time task queue statistics and lifecycle counts."""
    stats_data = await crud.get_queue_statistics(db, tenant_id=tenant.id)
    return QueueStatsResponse(**stats_data)


@router.post("/run", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def submit_agent_task(
    task_in: AgentSessionCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a new agent task for background execution with priority routing.
    Returns the created session ID (job_id) which can be polled for status.
    The task is dispatched to a Celery worker for async execution.
    """
    # --- Concurrency guard ---
    active_count = await crud.count_active_sessions(db, tenant_id=tenant.id)
    if active_count >= tenant.max_concurrent_sessions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Concurrency limit reached. You have {active_count} active "
                f"session(s) and your plan allows {tenant.max_concurrent_sessions}. "
                f"Wait for a running task to finish or cancel one."
            ),
        )

    queue_name = task_in.queue_name or "agents"
    priority = task_in.priority or 5
    if tenant.tier in [TenantTier.PRO, TenantTier.ENTERPRISE] and priority <= 3:
        queue_name = "priority_agents"

    session = await crud.create_session(
        db=db,
        tenant_id=tenant.id,
        task_prompt=task_in.task_prompt,
        target_url=task_in.target_url,
        user_id=getattr(tenant, "user_id", None),
        queue_name=queue_name,
        priority=priority,
        max_retries=task_in.max_retries or 3,
    )
    await db.commit()

    # --- Dispatch to background worker ---
    try:
        from workers.agent_tasks import run_agent_task
        from workers.dispatch import dispatch_task
        res = dispatch_task(run_agent_task, session.id, tenant.id, queue=queue_name, priority=priority)
        celery_task_id = getattr(res, "id", None)
        if celery_task_id:
            await crud.update_session_status(
                db, session.id, tenant.id, SessionStatus.QUEUED,
                celery_task_id=celery_task_id
            )
            await db.commit()
        logger.info(
            "Dispatched agent task: session=%s, tenant=%s, queue=%s",
            session.id, tenant.id, queue_name,
        )
    except Exception as e:
        logger.error("Failed to dispatch task: %s", e)

    return session


@router.get("/status/{job_id}", response_model=AgentSessionResponse)
async def get_agent_task_status(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status and result of a submitted agent task.
    """
    session = await crud.get_session(db, session_id=job_id, tenant_id=tenant.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session


@router.post("/cancel/{job_id}", response_model=Dict[str, Any])
async def cancel_agent_task(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a queued or running agent task.
    Updates the session status to CANCELLED and actively revokes running Celery worker task.
    """
    session = await crud.get_session(db, session_id=job_id, tenant_id=tenant.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED, SessionStatus.TIMED_OUT):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is already in terminal state: {session.status.value}"
        )

    # Update DB
    await crud.update_session_status(
        db,
        session_id=job_id,
        tenant_id=tenant.id,
        status=SessionStatus.CANCELLED,
        result_summary="Cancelled by user via API.",
    )

    # Also dispatch cancellation task to the worker queue
    try:
        from workers.agent_tasks import cancel_agent_task as cancel_task
        from workers.dispatch import dispatch_task
        dispatch_task(cancel_task, job_id, tenant.id, queue=session.queue_name)
    except Exception:
        pass  # DB update is the authoritative source

    logger.info("Cancelled agent task: session=%s", job_id)

    return {
        "status": "cancelled",
        "session_id": job_id,
        "message": "Session has been marked as cancelled.",
    }


@router.post("/retry/{job_id}", response_model=Dict[str, Any])
async def retry_agent_task(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry a stopped or failed agent task (DX Layer - Phase 5).
    Re-enqueues the task for Celery execution.
    """
    session = await crud.get_session(db, session_id=job_id, tenant_id=tenant.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status not in (SessionStatus.FAILED, SessionStatus.TIMED_OUT, SessionStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry session from state: {session.status.value}"
        )

    await crud.update_session_status(
        db,
        session_id=job_id,
        tenant_id=tenant.id,
        status=SessionStatus.QUEUED,
        error_message=None,
    )
    session.retry_count = (session.retry_count or 0) + 1
    await db.commit()

    try:
        from workers.agent_tasks import run_agent_task
        from workers.dispatch import dispatch_task
        dispatch_task(run_agent_task, job_id, tenant.id, queue=session.queue_name, priority=session.priority)
    except Exception as e:
        logger.error("Failed to re-dispatch task: %s", e)

    logger.info("Retried agent task: session=%s", job_id)

    return {
        "status": "queued",
        "session_id": job_id,
        "retry_count": session.retry_count,
        "message": "Session has been requeued.",
    }

