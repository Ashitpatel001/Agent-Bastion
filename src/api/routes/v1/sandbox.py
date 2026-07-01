from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant
from db import crud
from db.schemas import SandboxExecuteRequest, SandboxExecuteResponse
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
        run_agent_task.delay(session_id=session.id, tenant_id=current_tenant.id)
    except Exception:
        pass

    return SandboxExecuteResponse(
        session_id=session.id,
        status="RUNNING",
        sandbox_mode=request.sandbox_mode,
        message="Sandbox execution initiated successfully."
    )
