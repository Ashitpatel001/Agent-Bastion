from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from api.auth import get_current_tenant
from db.database import get_db
from db import crud
from db.models import Tenant
from db.schemas import AuditLogListResponse

router = APIRouter(prefix="/v1/security", tags=["Security Operations"])

@router.get("/logs", response_model=AuditLogListResponse)
async def get_security_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch paginated security audit logs for the authenticated tenant.
    """
    logs, total = await crud.list_audit_logs(
        db=db,
        tenant_id=tenant.id,
        page=page,
        page_size=page_size
    )
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": logs
    }

@router.get("/stats", response_model=Dict[str, Any])
async def get_security_stats(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch aggregated security statistics for the dashboard.
    """
    stats = await crud.get_audit_stats(db, tenant.id)
    return stats
