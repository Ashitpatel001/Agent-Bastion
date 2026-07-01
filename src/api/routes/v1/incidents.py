from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Any, List, Optional

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, Incident, IncidentComment, IncidentTimeline, IncidentSeverity, IncidentStatus
from db.schemas import (
    IncidentCreate, IncidentUpdate, IncidentResponse, 
    IncidentListResponse, IncidentCommentCreate, IncidentCommentResponse,
    IncidentTimelineResponse
)

router = APIRouter()

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_in: IncidentCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Manually create a security incident."""
    sev = IncidentSeverity.MEDIUM
    try:
        sev = IncidentSeverity(incident_in.severity)
    except Exception:
        pass

    inc = Incident(
        tenant_id=current_tenant.id,
        title=incident_in.title,
        description=incident_in.description,
        severity=sev,
        status=IncidentStatus.OPEN,
        session_id=incident_in.session_id,
        mitre_ids=incident_in.mitre_ids,
        labels=incident_in.labels,
    )
    db.add(inc)
    await db.flush()

    timeline = IncidentTimeline(
        incident_id=inc.id,
        event_type="CREATED",
        description=f"Incident created manually: {inc.title}"
    )
    db.add(timeline)
    await db.commit()
    await db.refresh(inc)
    return inc

@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List incidents for current tenant."""
    offset_val = skip if skip is not None else (page - 1) * page_size
    limit_val = limit if limit is not None else page_size

    count_res = await db.execute(select(func.count(Incident.id)).where(Incident.tenant_id == current_tenant.id))
    total = count_res.scalar_one()

    res = await db.execute(
        select(Incident)
        .where(Incident.tenant_id == current_tenant.id)
        .order_by(Incident.created_at.desc())
        .offset(offset_val)
        .limit(limit_val)
    )
    items = list(res.scalars().all())
    return {
        "total": total,
        "page": page if skip is None else (offset_val // limit_val) + 1,
        "page_size": limit_val,
        "items": items
    }

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get a specific incident."""
    res = await db.execute(select(Incident).where(Incident.id == incident_id, Incident.tenant_id == current_tenant.id))
    inc = res.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc

@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    incident_in: IncidentUpdate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update an incident."""
    res = await db.execute(select(Incident).where(Incident.id == incident_id, Incident.tenant_id == current_tenant.id))
    inc = res.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    data = incident_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "severity" and v:
            try:
                v = IncidentSeverity(v)
            except Exception:
                continue
        if k == "status" and v:
            try:
                v = IncidentStatus(v)
            except Exception:
                continue
        setattr(inc, k, v)

    await db.commit()
    await db.refresh(inc)
    return inc

@router.post("/{incident_id}/comments", response_model=IncidentCommentResponse)
async def add_incident_comment(
    incident_id: str,
    comment_in: IncidentCommentCreate,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Add a comment to an incident."""
    res = await db.execute(select(Incident).where(Incident.id == incident_id, Incident.tenant_id == current_tenant.id))
    inc = res.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    comm = IncidentComment(
        incident_id=inc.id,
        content=comment_in.content
    )
    db.add(comm)
    await db.commit()
    await db.refresh(comm)
    return comm

@router.get("/{incident_id}/timeline", response_model=List[IncidentTimelineResponse])
async def get_incident_timeline(
    incident_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get the full timeline of events for an incident."""
    res = await db.execute(select(IncidentTimeline).where(IncidentTimeline.incident_id == incident_id).order_by(IncidentTimeline.created_at.asc()))
    return list(res.scalars().all())
