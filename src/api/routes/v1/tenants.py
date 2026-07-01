from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from db.database import get_db
from db import crud, schemas
from api.auth import get_current_tenant
from db.models import Tenant

router = APIRouter()

@router.post("", response_model=schemas.TenantWithApiKey, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: schemas.TenantCreate, 
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new tenant."""
    tenant, raw_key = await crud.create_tenant(db, name=tenant_in.name, email=tenant_in.email)
    res = schemas.TenantWithApiKey.model_validate(tenant)
    res.api_key = raw_key
    return res

@router.get("/{tenant_id}", response_model=schemas.TenantResponse)
async def get_tenant(
    tenant_id: str,
    current_tenant: Tenant = Depends(get_current_tenant)
) -> Any:
    """Get tenant details. Requires authentication."""
    if current_tenant.id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return current_tenant
