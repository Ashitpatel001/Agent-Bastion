from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from db.database import get_db
from db import crud
from db.schemas import TenantCreate, TenantResponse

router = APIRouter(prefix="/v1/tenants", tags=["Tenants"])

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register_tenant(tenant_in: TenantCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new tenant. 
    This is typically an internal/admin endpoint or a public signup endpoint.
    Returns the created tenant and the RAW API KEY. 
    The raw API key is NEVER returned again, so it must be saved by the client.
    """
    # Check if email exists
    existing = await crud.get_tenant_by_email(db, tenant_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this email already exists."
        )
    
    tenant, raw_api_key = await crud.create_tenant(
        db=db,
        name=tenant_in.name,
        email=tenant_in.email
    )
    
    # We must construct a special response because TenantResponse doesn't include the raw key
    tenant_resp = TenantResponse.model_validate(tenant)
    return {
        "tenant": tenant_resp,
        "raw_api_key": raw_api_key,
        "message": "Store this API key securely. It will not be shown again."
    }
