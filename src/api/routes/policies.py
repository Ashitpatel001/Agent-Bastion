from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from api.auth import get_current_tenant
from db.database import get_db
from db import crud
from db.models import Tenant
from db.schemas import PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/v1/security/policies", tags=["Security Policies"])

@router.get("", response_model=PolicyResponse)
async def get_active_policy(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch the currently active security policy for the authenticated tenant.
    """
    policy = await crud.get_active_policy(db, tenant.id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active policy found for tenant"
        )
    return policy

@router.patch("", response_model=PolicyResponse)
async def update_policy(
    policy_in: PolicyUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the active policy. This creates a new version of the policy
    and deactivates the old one.
    """
    policy = await crud.update_policy(db, tenant.id, policy_in)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not update policy"
        )
    return policy
