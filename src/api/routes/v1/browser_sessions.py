from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, BrowserSessionRecord, BrowserSessionStatus
from db.schemas import BrowserSessionResponse, BrowserSessionListResponse

router = APIRouter()

@router.get("", response_model=BrowserSessionListResponse)
async def list_browser_sessions(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List browser sessions for current tenant."""
    count_res = await db.execute(select(func.count(BrowserSessionRecord.id)).where(BrowserSessionRecord.tenant_id == current_tenant.id))
    total = count_res.scalar_one()

    res = await db.execute(
        select(BrowserSessionRecord)
        .where(BrowserSessionRecord.tenant_id == current_tenant.id)
        .order_by(BrowserSessionRecord.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(res.scalars().all())
    return {
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit,
        "items": items
    }

@router.get("/{session_id}", response_model=BrowserSessionResponse)
async def get_browser_session(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get details for a specific browser session."""
    res = await db.execute(select(BrowserSessionRecord).where(BrowserSessionRecord.id == session_id, BrowserSessionRecord.tenant_id == current_tenant.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Browser session not found")
    return item

@router.post("/{session_id}/kill", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def kill_browser_session(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Forcibly terminate a browser session."""
    res = await db.execute(select(BrowserSessionRecord).where(BrowserSessionRecord.id == session_id, BrowserSessionRecord.tenant_id == current_tenant.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Browser session not found")
    item.status = BrowserSessionStatus.TERMINATED
    await db.commit()
