import logging
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from db.models import Tenant

logger = logging.getLogger("api.auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_tenant(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Dependency to authenticate a tenant via X-API-Key header.
    Returns the Tenant ORM object if successful, raises 401 otherwise.
    """
    if not api_key:
        logger.warning("Authentication failed: Missing X-API-Key header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    tenant = await crud.get_tenant_by_api_key(db, api_key)
    if not tenant:
        logger.warning(f"Authentication failed: Invalid API key used (prefix: {api_key[:12] if len(api_key)>12 else 'short'}).")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if not tenant.is_active:
        logger.warning(f"Authentication failed: Tenant '{tenant.name}' is inactive.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is disabled",
        )
    
    return tenant
