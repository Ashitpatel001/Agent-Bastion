from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, AgentSession, SessionStatus
from db.schemas import JobResponse, JobListResponse

router = APIRouter()

@router.get("", response_model=JobListResponse)
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List background agent jobs."""
    count_res = await db.execute(select(func.count(AgentSession.id)).where(AgentSession.tenant_id == current_tenant.id))
    total = count_res.scalar_one()

    res = await db.execute(
        select(AgentSession)
        .where(AgentSession.tenant_id == current_tenant.id)
        .order_by(AgentSession.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(res.scalars().all())
    job_items = [
        JobResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            task_name=item.task_prompt[:50] + ("..." if len(item.task_prompt) > 50 else ""),
            status=str(item.status.value if hasattr(item.status, 'value') else item.status),
            created_at=item.created_at,
            started_at=item.started_at,
            completed_at=item.completed_at,
            result=item.result_summary,
            error=item.error_message
        ) for item in items
    ]
    return {
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit,
        "items": job_items
    }

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get status of a specific background job."""
    res = await db.execute(select(AgentSession).where(AgentSession.id == job_id, AgentSession.tenant_id == current_tenant.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        task_name=item.task_prompt[:50],
        status=str(item.status.value if hasattr(item.status, 'value') else item.status),
        created_at=item.created_at,
        started_at=item.started_at,
        completed_at=item.completed_at,
        result=item.result_summary,
        error=item.error_message
    )

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def cancel_job(
    job_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Cancel a background job."""
    res = await db.execute(select(AgentSession).where(AgentSession.id == job_id, AgentSession.tenant_id == current_tenant.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    item.status = SessionStatus.CANCELLED
    await db.commit()
