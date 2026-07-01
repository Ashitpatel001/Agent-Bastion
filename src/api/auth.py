import logging
from datetime import datetime, timedelta
from typing import Optional, Union

from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
import bcrypt

from db.database import get_db
from db import crud
from db.models import Tenant, User
from security.config import SecurityConfig

logger = logging.getLogger("api.auth")

class _BcryptContext:
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

pwd_context = _BcryptContext()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SecurityConfig.JWT_SECRET_KEY, algorithm=SecurityConfig.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to authenticate a user via JWT."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        
    # Inject context for structured logging
    from security.logger import request_context
    ctx = request_context.get()
    ctx.update({"user_id": user.id, "tenant_id": user.tenant_id})
    request_context.set(ctx)
    
    return user


async def get_current_tenant(
    token: str = Depends(oauth2_scheme),
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Dependency to authenticate a tenant.
    Supports BOTH JWT (User-driven) and X-API-Key (Service-driven).
    """
    from security.logger import request_context

    if token:
        # Try JWT authentication first
        try:
            payload = jwt.decode(token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                tenant = await db.get(Tenant, tenant_id)
                if tenant and tenant.is_active:
                    ctx = request_context.get()
                    ctx.update({"tenant_id": tenant.id})
                    request_context.set(ctx)
                    return tenant
        except JWTError:
            pass # Fall back to API Key if JWT fails or is invalid

    if api_key:
        # Try API Key authentication (Fallback for frontend or service-to-service)
        tenant = await crud.get_tenant_by_api_key(db, api_key)
        if tenant and tenant.is_active:
            ctx = request_context.get()
            ctx.update({"tenant_id": tenant.id})
            request_context.set(ctx)
            return tenant
            
    # If both failed or were missing
    logger.warning("Authentication failed: Missing or invalid credentials.")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


from typing import List
from db.models import UserRole

class RequireRole:
    """
    Role-Based Access Control (RBAC) dependency.
    Extends get_current_tenant by enforcing roles when a JWT is used.
    If authenticated via an API key, we assume system/service-level access and bypass user roles.
    """
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        token: str = Depends(oauth2_scheme),
        api_key: str = Security(api_key_header),
        db: AsyncSession = Depends(get_db)
    ) -> Tenant:
        # Authenticate tenant using existing logic
        tenant = await get_current_tenant(token=token, api_key=api_key, db=db)
        
        # If API key is present and valid, bypass user role check
        if not token and api_key:
            return tenant
            
        # If token is present, evaluate user role
        try:
            payload = jwt.decode(token, SecurityConfig.JWT_SECRET_KEY, algorithms=[SecurityConfig.JWT_ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
                
            user = await db.get(User, user_id)
            if not user or user.role not in self.allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Operation not permitted. Requires one of: {[r.value for r in self.allowed_roles]}"
                )
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            
        return tenant
