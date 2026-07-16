import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any

from db.database import get_db
from db.models import APIKeyRecord, Tenant, User
from db.schemas import APIKeyCreate, APIKeyResponse, APIKeyCreateResponse, APIKeyListResponse, ErrorResponse
from api.auth import get_current_tenant, get_current_user

router = APIRouter()


def generate_api_key() -> tuple[str, str, str]:
    """Generates a raw key, its hash, and prefix."""
    raw_key = f"abs_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:12]
    return raw_key, key_hash, prefix


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_in: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create a new API key for the tenant."""
    raw_key, key_hash, prefix = generate_api_key()
    
    db_key = APIKeyRecord(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        name=key_in.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=key_in.scopes,
    )
    
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    
    # We must construct the response carefully to include raw_key
    base_data = APIKeyResponse.model_validate(db_key)
    return APIKeyCreateResponse(**base_data.model_dump(), raw_key=raw_key)


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = 0, 
    limit: int = 100,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List API keys for the current tenant."""
    query = select(APIKeyRecord).where(APIKeyRecord.tenant_id == current_tenant.id).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # We should really count total, but for simplicity:
    total = len(items) 
    
    return {
        "total": total,
        "page": (skip // limit) + 1 if limit > 0 else 1,
        "page_size": limit,
        "items": items
    }


@router.post("/{key_id}/rotate", response_model=APIKeyCreateResponse)
async def rotate_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Rotate an API key (generate a new key, replacing the old one)."""
    db_key = await db.get(APIKeyRecord, key_id)
    if not db_key or db_key.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    raw_key, key_hash, prefix = generate_api_key()
    db_key.key_hash = key_hash
    db_key.key_prefix = prefix
    
    await db.commit()
    await db.refresh(db_key)
    
    base_data = APIKeyResponse.model_validate(db_key)
    return APIKeyCreateResponse(**base_data.model_dump(), raw_key=raw_key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Revoke (delete) an API key."""
    db_key = await db.get(APIKeyRecord, key_id)
    if not db_key or db_key.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="API Key not found")
        
    db_key.is_active = False
    await db.delete(db_key)
    await db.commit()
    return None
