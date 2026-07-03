import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from api.auth import get_current_tenant
from db.database import get_db
from db import crud
from db.models import Tenant
from db.schemas import AgentSessionCreate, AgentSessionResponse

logger = logging.getLogger("api.routes.agents")

router = APIRouter(prefix="/v1/agent", tags=["Agent Tasks"])

@router.post("/run", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def submit_agent_task(
    task_in: AgentSessionCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a new agent task for background execution.
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

    session = await crud.create_session(
        db=db,
        tenant_id=tenant.id,
        task_prompt=task_in.task_prompt,
        target_url=task_in.target_url
    )
    await db.commit()

    # --- Dispatch to background worker ---
    try:
        from workers.agent_tasks import run_agent_task
        from workers.dispatch import dispatch_task
        dispatch_task(run_agent_task, session.id, tenant.id)
        logger.info(
            "Dispatched agent task: session=%s, tenant=%s",
            session.id, tenant.id,
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
    Updates the session status to CANCELLED. Does not forcefully
    terminate a running browser — the worker will detect the status
    change on its next checkpoint.
    """
    from db.models import SessionStatus

    session = await crud.get_session(db, session_id=job_id, tenant_id=tenant.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED):
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
        cancel_task.delay(job_id, tenant.id)
    except Exception:
        pass  # DB update is the authoritative source

    logger.info("Cancelled agent task: session=%s", job_id)

    return {
        "status": "cancelled",
        "session_id": job_id,
        "message": "Session has been marked as cancelled.",
    }

