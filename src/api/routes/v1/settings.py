from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, TenantSettings
from db.schemas import TenantSettingsUpdate, TenantSettingsResponse

router = APIRouter()

async def get_or_create_settings(db: AsyncSession, tenant_id: str) -> TenantSettings:
    res = await db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
    s = res.scalar_one_or_none()
    if not s:
        s = TenantSettings(tenant_id=tenant_id)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s

@router.get("", response_model=TenantSettingsResponse)
async def get_tenant_settings(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get tenant settings."""
    return await get_or_create_settings(db, current_tenant.id)

@router.patch("", response_model=TenantSettingsResponse)
async def update_tenant_settings(
    settings_in: TenantSettingsUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update tenant settings."""
    s = await get_or_create_settings(db, current_tenant.id)
    data = settings_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return s
