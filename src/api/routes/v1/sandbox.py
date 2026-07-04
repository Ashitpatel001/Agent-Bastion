from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from db.database import get_db
from api.auth import get_current_tenant
from db.models import Tenant, SessionStatus
from db import crud
from db.schemas import (
    SandboxExecuteRequest,
    SandboxExecuteResponse,
    SandboxSessionResponse,
    SandboxListResponse,
)
from workers.agent_tasks import run_agent_task
import asyncio
from datetime import datetime, timezone, timedelta
from db.models import AuditLog, Incident, IncidentTimeline, IncidentSeverity, IncidentStatus, SecurityEvent, RiskLevel, ActionTaken

router = APIRouter()

@router.post("/execute", response_model=SandboxExecuteResponse)
async def execute_in_sandbox(
    request: SandboxExecuteRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Execute code or prompt in an isolated sandbox."""
    session = await crud.create_session(
        db=db,
        tenant_id=current_tenant.id,
        task_prompt=request.task_prompt,
        target_url=request.target_url
    )
    await db.commit()
    try:
        from workers.dispatch import dispatch_task
        dispatch_task(run_agent_task, session.id, current_tenant.id)
    except Exception as e:
        await crud.update_session_status(
            db=db,
            session_id=session.id,
            tenant_id=current_tenant.id,
            status=SessionStatus.FAILED,
            error_message=f"Failed to dispatch execution: {str(e)}"
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate sandbox execution: {str(e)}"
        )

    return SandboxExecuteResponse(
        session_id=session.id,
        status="RUNNING",
        sandbox_mode=request.sandbox_mode,
        message="Sandbox execution initiated successfully."
    )


@router.get("/list", response_model=SandboxListResponse)
@router.get("", response_model=SandboxListResponse)
async def list_sandbox_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List sandbox execution sessions for current tenant."""
    items, total = await crud.list_sessions(
        db=db,
        tenant_id=current_tenant.id,
        page=page,
        page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    }


@router.get("/{session_id}", response_model=SandboxSessionResponse)
async def get_sandbox_session(
    session_id: str,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get details for a specific sandbox execution session."""
    session = await crud.get_session(db, session_id=session_id, tenant_id=current_tenant.id)
    if not session:
        raise HTTPException(status_code=404, detail="Sandbox session not found")
    return session

@router.post("/simulate-traffic")
async def simulate_proxy_traffic(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Generate dummy traffic for the dashboard."""
    now = datetime.now(timezone.utc)
    sample_logs = [
        {
            "event_type": "PROMPT_INJECTION_BLOCKED",
            "url": "https://suspicious-vendor-portal.io/invoice",
            "details": "DOM Sanitizer Lens intercepted hidden adversarial prompt.",
            "risk_level": RiskLevel.CRITICAL,
            "risk_score": 94,
            "action_taken": ActionTaken.BLOCK_AND_ESCALATE,
            "xai_explanation": "XAI Deep Inspection: Neural DOM analyzer identified hidden CSS layer.",
        },
        {
            "event_type": "API_TRAFFIC_VERIFIED",
            "url": "https://api.stripe.com/v1/payment_intents/create",
            "details": "Autonomous billing agent executed Stripe API reconciliation within verified trusted origin bounds.",
            "risk_level": RiskLevel.SAFE,
            "risk_score": 12,
            "action_taken": ActionTaken.ALLOWED,
            "xai_explanation": "XAI Trust Verification: Domain 'api.stripe.com' validated.",
        },
        {
            "event_type": "CREDENTIAL_DUMP_PREVENTED",
            "url": "http://internal-app.local/login",
            "details": "Agent attempted to populate form input matching honey token credit card regex pattern.",
            "risk_level": RiskLevel.HIGH,
            "risk_score": 88,
            "action_taken": ActionTaken.BLOCKED,
            "xai_explanation": "XAI DLP Firewall Analysis: Input payload matched sensitive regex signature.",
        }
    ]

    for idx, log_data in enumerate(sample_logs):
        t_offset = timedelta(minutes=idx * 5)
        audit = AuditLog(
            tenant_id=current_tenant.id,
            event_type=log_data["event_type"],
            url=log_data["url"],
            details=log_data["details"],
            risk_level=log_data["risk_level"],
            risk_score=log_data["risk_score"],
            action_taken=log_data["action_taken"],
            xai_explanation=log_data["xai_explanation"],
            xai_pending=False,
            created_at=now - t_offset
        )
        db.add(audit)
        
        sec_ev = SecurityEvent(
            tenant_id=current_tenant.id,
            event_type=log_data["event_type"],
            severity=log_data["risk_level"],
            source=log_data["url"],
            details=log_data["details"],
            created_at=now - t_offset
        )
        db.add(sec_ev)

    inc = Incident(
        tenant_id=current_tenant.id,
        title="[CRITICAL] Simulated Attack Intercepted",
        description="A simulated prompt injection attack was blocked.",
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.OPEN,
        risk_score=94,
        mitre_ids=["T1566"],
        labels=["prompt-injection", "simulation"],
        created_at=now
    )
    db.add(inc)
    await db.flush()

    tl = IncidentTimeline(
        incident_id=inc.id,
        event_type="ALERT_ESCALATED",
        description="Simulated alert escalated to SOC."
    )
    db.add(tl)
    await db.commit()
    return {"status": "success", "message": "Traffic simulated successfully"}
