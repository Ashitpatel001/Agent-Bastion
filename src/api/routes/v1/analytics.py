import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant
from db import crud

logger = logging.getLogger("api.routes.v1.analytics")
router = APIRouter()


@router.get("/overview")
async def get_analytics_overview(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated analytics overview with real data from audit logs."""
    stats = await crud.get_audit_stats(db, current_tenant.id)
    return stats


@router.get("/time-series")
async def get_analytics_time_series(
    days: int = Query(default=30, ge=1, le=365),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get daily time-series data for dashboard charts."""
    data = await crud.get_time_series_stats(db, current_tenant.id, days=days)
    return {"days": days, "data": data}


