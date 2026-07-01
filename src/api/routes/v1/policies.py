from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from db.database import get_db
from db import crud, schemas
from api.auth import get_current_tenant
from db.models import Tenant

router = APIRouter()

@router.get("", response_model=schemas.PolicyResponse)
async def get_active_policy(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get the active security policy for the tenant."""
    policy = await crud.get_active_policy(db, current_tenant.id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.patch("", response_model=schemas.PolicyResponse)
async def update_policy(
    policy_in: schemas.PolicyUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update the security policy."""
    policy = await crud.update_policy(db, current_tenant.id, policy_in)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
