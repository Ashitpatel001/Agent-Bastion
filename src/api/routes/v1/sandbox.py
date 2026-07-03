from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, SessionStatus
from db import crud
from db.schemas import (
    SandboxExecuteRequest,
    SandboxExecuteResponse,
    SandboxSessionResponse,
    SandboxListResponse,
)
from workers.agent_tasks import run_agent_task

router = APIRouter()

@router.post("/execute", response_model=SandboxExecuteResponse)
async def execute_in_sandbox(
    request: SandboxExecuteRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Execute code or prompt in an isolated sandbox."""
    session = await crud.create_session(
        db=db,
        tenant_id=current_tenant.id,
        task_prompt=request.task_prompt,
        target_url=request.target_url
    )
    await db.commit()
    try:
        from workers.dispatch import dispatch_task
        dispatch_task(run_agent_task, session.id, current_tenant.id)
    except Exception as e:
        await crud.update_session_status(
            db=db,
            session_id=session.id,
            tenant_id=current_tenant.id,
            status=SessionStatus.FAILED,
            error_message=f"Failed to dispatch execution: {str(e)}"
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate sandbox execution: {str(e)}"
        )

    return SandboxExecuteResponse(
        session_id=session.id,
        status="RUNNING",
        sandbox_mode=request.sandbox_mode,
        message="Sandbox execution initiated successfully."
    )


@router.get("/list", response_model=SandboxListResponse)
@router.get("", response_model=SandboxListResponse)
async def list_sandbox_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List sandbox execution sessions for current tenant."""
    items, total = await crud.list_sessions(
        db=db,
        tenant_id=current_tenant.id,
        page=page,
        page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.get("/{session_id}", response_model=SandboxSessionResponse)
async def get_sandbox_session(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get details for a specific sandbox execution session."""
    session = await crud.get_session(db, session_id=session_id, tenant_id=current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Sandbox session not found")
    return session
