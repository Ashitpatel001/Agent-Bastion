from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from db.database import get_db
from db import crud, schemas
from api.auth import get_current_tenant
from db.models import Tenant, SessionStatus
from workers.agent_tasks import run_agent_task

router = APIRouter()

@router.post("", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def submit_agent_task(
    request: schemas.AgentSessionCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Submit a new autonomous agent task."""
    session = await crud.create_session(
        db, 
        tenant_id=current_tenant.id,
        task_prompt=request.task_prompt,
        target_url=request.target_url
    )
    
    # Enqueue Celery task
    run_agent_task.delay(session.id, current_tenant.id, request.task_prompt, request.target_url)
    
    return {"session_id": session.id, "status": "QUEUED"}

@router.get("/{session_id}", response_model=schemas.AgentSessionResponse)
async def get_agent_status(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get the status of an agent session."""
    session = await crud.get_session(db, session_id, current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/cancel", response_model=Dict[str, str])
async def cancel_agent_task(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Cancel a running agent task."""
    session = await crud.get_session(db, session_id, current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Cannot cancel a finished session")
        
    await crud.update_session_status(db, session_id, SessionStatus.CANCELLED)
    
    return {"session_id": session_id, "status": "CANCELLED"}
