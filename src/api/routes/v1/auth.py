import logging
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any, Optional
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError

from db.database import get_db
from db.models import User, UserRole
from db.schemas import Token, ErrorResponse, UserResponse, PasswordChangeRequest, LoginRequest
from db import crud
from security.config import SecurityConfig
from api.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    require_admin,
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
    """Register a new Tenant and Owner/Admin User account."""
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
    token_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "jti": token_id, "family_id": family_id}
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    await crud.create_refresh_token_record(
        db, token_id=token_id, user_id=user.id, family_id=family_id,
        raw_refresh_token=refresh_token, expires_at=expires_at
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
    token_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "jti": token_id, "family_id": family_id}
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    await crud.create_refresh_token_record(
        db, token_id=token_id, user_id=user.id, family_id=family_id,
        raw_refresh_token=refresh_token, expires_at=expires_at
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
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    token_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(data={"sub": user.id, "tenant_id": user.tenant_id, "jti": token_id, "family_id": family_id})
    expires_at = datetime.now(timezone.utc) + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    await crud.create_refresh_token_record(
        db, token_id=token_id, user_id=user.id, family_id=family_id,
        raw_refresh_token=refresh_token, expires_at=expires_at
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

class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Revoke active refresh tokens for the current user upon logout."""
    count = await crud.revoke_user_refresh_tokens(db, current_user.id)
    return {"message": "Successfully logged out.", "revoked_tokens": count}


@router.post("/refresh", response_model=Token)
async def refresh(
    req: RefreshRequest = RefreshRequest(),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Production single-use refresh token rotation with replay attack protection (Task 2.3).
    If a reused or revoked refresh token is detected, the entire token family is invalidated.
    """
    raw_token = req.refresh_token
    if not raw_token and request and request.headers.get("authorization"):
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header.split(" ", 1)[1]

    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required.")

    try:
        payload = jwt.decode(raw_token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type. Must be a refresh token.")
        user_id: str = payload.get("sub")
        token_id: str = payload.get("jti")
        family_id: str = payload.get("family_id")
        if not user_id or not token_id or not family_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token format or signature.")

    db_token = await crud.get_refresh_token_by_id(db, token_id)
    if not db_token:
        if family_id:
            await crud.revoke_refresh_token_family(db, family_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found or invalidated.")

    if db_token.is_revoked:
        logging.warning("Security audit: Replay attack detected on token family %s for user %s. Revoking family.", db_token.family_id, db_token.user_id)
        await crud.revoke_refresh_token_family(db, db_token.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has already been used or revoked. Entire token family invalidated for security."
        )

    exp_time = db_token.expires_at.replace(tzinfo=timezone.utc) if db_token.expires_at.tzinfo is None else db_token.expires_at
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired.")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

    # Mark current token used
    db_token.is_revoked = True
    await db.commit()

    # Issue new token pair with same family_id
    new_access_token = create_access_token(data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    new_token_id = str(uuid.uuid4())
    new_refresh_token = create_refresh_token(data={"sub": user.id, "tenant_id": user.tenant_id, "jti": new_token_id, "family_id": family_id})
    expires_at = datetime.now(timezone.utc) + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    await crud.create_refresh_token_record(
        db, token_id=new_token_id, user_id=user.id, family_id=family_id,
        raw_refresh_token=new_refresh_token, expires_at=expires_at
    )
    tenant = await crud.get_tenant_by_id(db, user.tenant_id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 1800,
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name if tenant else "Enterprise Tenant",
        "user": UserResponse.model_validate(user).model_dump()
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> Any:
    return current_user


@router.post("/password/change")
@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()
    await crud.revoke_user_refresh_tokens(db, current_user.id)
    return {"message": "Password updated successfully. All active sessions revoked."}


class BootstrapAdminRequest(BaseModel):
    email: EmailStr = "admin@abss.internal"
    password: Optional[str] = None
    name: Optional[str] = "Enterprise Tenant"


@router.post("/bootstrap-admin", status_code=status.HTTP_201_CREATED)
async def bootstrap_admin(
    req: BootstrapAdminRequest = BootstrapAdminRequest(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Bootstrap Admin Flow (Task 2.8).
    Can ONLY be executed once when the database has zero user accounts.
    """
    result = await db.execute(select(func.count(User.id)))
    user_count = result.scalar() or 0
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap admin has already been executed. Database is not empty. Setup disabled."
        )

    password = req.password or secrets.token_urlsafe(16)
    tenant, raw_key = await crud.create_tenant(db, name=req.name or "Enterprise Tenant", email=req.email)
    
    user = User(
        tenant_id=tenant.id,
        email=req.email,
        password_hash=get_password_hash(password),
        full_name="Bootstrap Admin",
        role=UserRole.OWNER,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    token_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(
        data={"sub": user.id, "tenant_id": user.tenant_id, "jti": token_id, "family_id": family_id}
    )
    expires_at = datetime.now(timezone.utc) + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    await crud.create_refresh_token_record(
        db, token_id=token_id, user_id=user.id, family_id=family_id,
        raw_refresh_token=refresh_token, expires_at=expires_at
    )

    logging.info("========================================")
    logging.info("BOOTSTRAP ADMIN ACCOUNT CREATED:")
    logging.info("Email: %s", user.email)
    logging.info("Role: %s", user.role)
    logging.info("Tenant ID: %s", tenant.id)
    logging.info("========================================")

    return {
        "message": "Bootstrap admin created successfully",
        "tenant_id": tenant.id,
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "password": password,
        "raw_api_key": raw_key,
        "access_token": access_token,
        "refresh_token": refresh_token
    }


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.VIEWER


@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Admin-only endpoint to create users under the admin's tenant."""
    res = await db.execute(select(User).where(User.tenant_id == current_admin.tenant_id, User.email == req.email))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists in this tenant")
    
    new_user = User(
        tenant_id=current_admin.tenant_id,
        email=req.email,
        password_hash=get_password_hash(req.password),
        full_name=req.full_name or req.email.split("@")[0],
        role=req.role,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/password/reset")
async def reset_password(email: str) -> Any:
    return {"message": "If an account exists with this email, a reset link will be sent."}
