from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant, get_password_hash
from db.models import Tenant, User, UserRole
from db.schemas import UserCreate, UserUpdate, UserResponse, UserListResponse

router = APIRouter()

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new user within the current tenant."""
    # check email uq
    res = await db.execute(select(User).where(User.tenant_id == current_tenant.id, User.email == user_in.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists in tenant.")

    role_val = UserRole.VIEWER
    try:
        role_val = UserRole(user_in.role)
    except Exception:
        pass

    user = User(
        tenant_id=current_tenant.id,
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=role_val,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List users for the current tenant."""
    count_res = await db.execute(select(func.count(User.id)).where(User.tenant_id == current_tenant.id))
    total = count_res.scalar_one()

    res = await db.execute(
        select(User)
        .where(User.tenant_id == current_tenant.id)
        .order_by(User.created_at.desc())
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

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a specific user by ID."""
    res = await db.execute(select(User).where(User.id == user_id, User.tenant_id == current_tenant.id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update a user."""
    res = await db.execute(select(User).where(User.id == user_id, User.tenant_id == current_tenant.id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    data = user_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "role" and v:
            try:
                v = UserRole(v)
            except Exception:
                continue
        setattr(user, k, v)

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user(
    user_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete a user."""
    res = await db.execute(select(User).where(User.id == user_id, User.tenant_id == current_tenant.id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
