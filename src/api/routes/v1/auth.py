import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Optional
from pydantic import BaseModel, EmailStr

from db.database import get_db
from db.models import User, UserRole
from db.schemas import Token, ErrorResponse, UserResponse, PasswordChangeRequest, LoginRequest
from db import crud
from api.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_password,
    get_password_hash
)

router = APIRouter()

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    full_name: Optional[str] = "Admin User"

class RegisterResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: str
    tenant_name: str
    raw_api_key: str
    user: UserResponse

async def authenticate_user_logic(db: AsyncSession, email: str, password: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

@router.post("/register", response_model=RegisterResponse)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new Tenant and Owner User account."""
    existing_t = await crud.get_tenant_by_email(db, req.email)
    if existing_t:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    tenant, raw_key = await crud.create_tenant(db, name=req.name, email=req.email)
    
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        password_hash=get_password_hash(req.password),
        full_name=req.full_name or "Admin User",
        role=UserRole.OWNER,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "tenant_id": user.tenant_id}
    )

    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        raw_api_key=raw_key,
        user=UserResponse.model_validate(user)
    )

@router.post("/login", response_model=Token, responses={401: {"model": ErrorResponse}})
async def login_json(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Authenticate via JSON email/password and return tokens."""
    user = await authenticate_user_logic(db, req.email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "tenant_id": user.tenant_id}
    )
    tenant = await crud.get_tenant_by_id(db, user.tenant_id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name if tenant else "Enterprise Tenant",
        "user": UserResponse.model_validate(user).model_dump()
    }

@router.post("/token", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Authenticate via OAuth2 Form data (for Swagger UI compatibility)."""
    user = await authenticate_user_logic(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.id, "tenant_id": user.tenant_id})
    tenant = await crud.get_tenant_by_id(db, user.tenant_id)
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token, 
        "token_type": "bearer", 
        "expires_in": 1800,
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name if tenant else "Enterprise Tenant",
        "user": UserResponse.model_validate(user).model_dump()
    }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> Any:
    return {"message": "Successfully logged out."}

@router.post("/refresh", response_model=Token)
async def refresh(current_user: User = Depends(get_current_user)) -> Any:
    access_token = create_access_token(data={"sub": current_user.id, "tenant_id": current_user.tenant_id, "role": current_user.role})
    return {"access_token": access_token, "refresh_token": "keep-existing-refresh-token", "token_type": "bearer", "expires_in": 1800}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> Any:
    return current_user

@router.post("/password/change")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.post("/password/reset")
async def reset_password(email: str) -> Any:
    return {"message": "If an account exists with this email, a reset link will be sent."}
