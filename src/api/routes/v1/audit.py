from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from db.database import get_db
from db import crud, schemas
from api.auth import get_current_tenant
from db.models import Tenant

router = APIRouter()

@router.get("", response_model=schemas.AuditLogListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    pending_only: bool = Query(False),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get paginated audit logs with XAI explanations for the current tenant."""
    logs, total = await crud.get_xai_audit_logs(
        db, current_tenant.id, page=page, page_size=page_size, pending_only=pending_only
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": logs
    }
