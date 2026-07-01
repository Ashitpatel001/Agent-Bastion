from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, Organization
from db.schemas import OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationListResponse

router = APIRouter()

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_in: OrganizationCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new organization."""
    org = Organization(
        owner_tenant_id=current_tenant.id,
        name=org_in.name,
        slug=org_in.slug,
        description=org_in.description,
        is_active=True
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org

@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List organizations."""
    count_res = await db.execute(select(func.count(Organization.id)).where(Organization.owner_tenant_id == current_tenant.id))
    total = count_res.scalar_one()

    res = await db.execute(
        select(Organization)
        .where(Organization.owner_tenant_id == current_tenant.id)
        .order_by(Organization.created_at.desc())
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

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a specific organization by ID."""
    res = await db.execute(select(Organization).where(Organization.id == org_id, Organization.owner_tenant_id == current_tenant.id))
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_in: OrganizationUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update an organization."""
    res = await db.execute(select(Organization).where(Organization.id == org_id, Organization.owner_tenant_id == current_tenant.id))
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    data = org_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(org, k, v)
    await db.commit()
    await db.refresh(org)
    return org
