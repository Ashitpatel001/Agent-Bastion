from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any, Optional

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, SecurityEvent
from db.schemas import SecurityEventResponse, SecurityEventListResponse

router = APIRouter()

@router.get("", response_model=SecurityEventListResponse)
async def list_security_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List security events for current tenant."""
    offset_val = skip if skip is not None else (page - 1) * page_size
    limit_val = limit if limit is not None else page_size

    count_res = await db.execute(select(func.count(SecurityEvent.id)).where(SecurityEvent.tenant_id == current_tenant.id))
    total = count_res.scalar_one()

    res = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.tenant_id == current_tenant.id)
        .order_by(SecurityEvent.created_at.desc())
        .offset(offset_val)
        .limit(limit_val)
    )
    items = list(res.scalars().all())
    return {
        "total": total,
        "page": page if skip is None else (offset_val // limit_val) + 1,
        "page_size": limit_val,
        "items": items
    }

@router.get("/{event_id}", response_model=SecurityEventResponse)
async def get_security_event(
    event_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get details of a specific security event."""
    res = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id, SecurityEvent.tenant_id == current_tenant.id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Security event not found")
    return item
