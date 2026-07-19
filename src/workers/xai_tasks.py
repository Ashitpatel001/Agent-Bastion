"""
workers/xai_tasks.py — Async XAI Explanation Generation.

Celery tasks that generate human-readable explanations for blocked
agent actions using Google Gemini (or any LangChain-compatible LLM).

Design:
  When SecureAgent blocks an action, it:
    1. Instantly inserts an audit log with xai_pending=True and
       xai_explanation="Generating explanation..."
    2. Fires `generate_xai_explanation.delay(log_id, payload)` to this worker.
  The worker:
    1. Calls the LLM to generate the explanation.
    2. Updates the audit log row with the real explanation (xai_pending=False).

  This decouples the LLM latency from the agent's hot path, reducing
  step execution time from ~2-4s (with XAI) to ~50ms (fire-and-forget).

Queue: 'xai' (see celery_app.py task_routes).

Usage:
    # Start XAI worker:
    celery -A workers.celery_app worker -Q xai --loglevel=info --concurrency=4

    # Backfill pending XAI explanations:
    # Use generate_xai_batch task with a list of log_id + payload pairs.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
from api.config import settings

GROQ_API_KEY = settings.GROQ_API_KEY
XAI_MODEL = settings.XAI_MODEL

# Maximum retries and backoff for transient LLM failures
_MAX_RETRIES = 3
_RETRY_BACKOFF = 30  # seconds (exponential: 30, 60, 120)


# ---------------------------------------------------------------------------
# Async ↔ Sync Bridge
# ---------------------------------------------------------------------------
def _run_async(coro):
    """
    Run an async coroutine from synchronous Celery task context.

    Creates a fresh event loop per invocation to avoid conflicts with
    the Celery worker's own event loop management. This is safe because
    Celery tasks run in their own thread/process.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------
async def _update_audit_log(log_id: str, explanation: str) -> None:
    """
    Write the generated XAI explanation back to the database and
    clear the xai_pending flag.

    Uses get_db_context() (the standalone context manager) rather than
    get_db() (the FastAPI dependency) since we're outside a request.
    """
    from db.database import get_db_context
    from db import crud

    async with get_db_context() as db:
        success = await crud.update_audit_xai_explanation(
            db, log_id=log_id, explanation=explanation
        )
        if success:
            logger.info("XAI explanation saved for audit log %s", log_id)
        else:
            logger.warning("Audit log %s not found for XAI backfill", log_id)


async def _get_pending_xai_logs(
    tenant_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Fetch audit logs that have xai_pending=True for backfill processing.
    """
    from db.database import get_db_context
    from sqlalchemy import select
    from db.models import AuditLog

    async with get_db_context() as db:
        stmt = (
            select(AuditLog)
            .where(AuditLog.xai_pending == True)  # noqa: E712
            .order_by(AuditLog.created_at.asc())
            .limit(limit)
        )
        if tenant_id:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)

        result = await db.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "log_id": log.id,
                "payload": {
                    "action_data": log.details or "",
                    "risk_score": log.risk_score or 0,
                    "reason": log.details or "Unknown",
                    "risk_level": (
                        log.risk_level.value
                        if hasattr(log.risk_level, "value")
                        else str(log.risk_level)
                    ),
                    "breakdown": log.risk_breakdown or {},
                    "url": log.url or "",
                    "security_state": "UNKNOWN",
                },
            }
            for log in logs
        ]


# ---------------------------------------------------------------------------
# LLM Explanation Generation
# ---------------------------------------------------------------------------
def _template_fallback(payload: Dict[str, Any]) -> str:
    """
    Generate a structured template explanation fallback when LLM call fails or API key is missing.
    """
    risk_score = payload.get("risk_score", 0)
    reason = payload.get("reason", "Unknown security violation")
    risk_level = payload.get("risk_level", "HIGH")
    url = payload.get("url", "target site")

    return (
        f"The attempted action on {url} was blocked by enterprise security policy due to: {reason}. "
        f"This activity triggered a {risk_level} risk classification (Score: {risk_score}/100). "
        f"Allowing this interaction could have resulted in unauthorized data exfiltration or policy non-compliance."
    )


async def _generate_explanation_llm(payload: Dict[str, Any]) -> str:
    """
    Call the LLM to generate a security explanation.

    Uses LangChain's ChatGroq, falling back
    to a structured template if the LLM call fails or API key is missing.
    """

    action_data = payload.get("action_data", "{}")
    risk_score = payload.get("risk_score", 0)
    reason = payload.get("reason", "Unknown")
    risk_level = payload.get("risk_level", "HIGH")
    breakdown = payload.get("breakdown", {})
    url = payload.get("url", "")
    security_state = payload.get("security_state", "UNKNOWN")

    xai_prompt = (
        "You are a cybersecurity analyst working in a Security Operations Center (SOC). "
        "A browser automation agent had an action BLOCKED by the ABSs security system. "
        "Write a clear, professional 2-3 sentence explanation for the human operator "
        "covering:\n"
        "1. WHAT the agent tried to do\n"
        "2. WHY it was blocked (cite specific risk signals)\n"
        "3. The RISK to the organisation if this action had been allowed\n\n"
        f"Action attempted: {str(action_data)[:300]}\n"
        f"Target URL: {url}\n"
        f"Risk Score: {risk_score}/100\n"
        f"Risk Level: {risk_level}\n"
        f"Block Reason: {reason}\n"
        f"Risk Breakdown: {json.dumps(breakdown, default=str)}\n"
        f"Session Security State: {security_state}\n\n"
        "Write ONLY the explanation. Be concise, specific, and actionable. "
        "Do not use markdown formatting or headers."
    )

    # Fallback if no API key
    llm = None
    if settings.PRIMARY_LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=settings.OPENAI_MODEL if hasattr(settings, "OPENAI_MODEL") else "gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0.3)
    elif settings.PRIMARY_LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=settings.XAI_MODEL, google_api_key=settings.GEMINI_API_KEY, temperature=0.3)
    elif settings.PRIMARY_LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        llm = ChatGroq(model=settings.XAI_MODEL, api_key=settings.GROQ_API_KEY, temperature=0.3)

    if not llm:
        logger.warning("No valid LLM configuration found for XAI - using template fallback.")
        return _template_fallback(payload)

    try:
        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=xai_prompt)])
        explanation = response.content.strip()

        if not explanation:
            return _template_fallback(payload)

        return explanation

    except Exception as exc:
        logger.exception("XAI generation failed: %s", exc)
        return _template_fallback(payload)

# Celery Tasks

@shared_task(
    bind=True,
    name="workers.xai_tasks.generate_xai_explanation",
    max_retries=_MAX_RETRIES,
    default_retry_delay=_RETRY_BACKOFF,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
    queue="xai",
    soft_time_limit=120,
    time_limit=150,
)
def generate_xai_explanation(
    self,
    log_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate an XAI explanation for a blocked action and backfill
    the audit log.

    This is the primary task fired by SecureAgent._generate_xai_explanation()
    after it inserts a pending audit log entry.

    Args:
        log_id:   The audit_log.id to update once the explanation is ready.
        payload:  Dict containing:
            - action_data (str): JSON-serialized action the agent attempted.
            - risk_score (int): Numeric risk score (0-100).
            - reason (str): Human-readable block reason.
            - risk_level (str): Risk classification (LOW/MEDIUM/HIGH/CRITICAL).
            - breakdown (dict): Detailed risk signal breakdown.
            - url (str): Target URL at time of block.
            - security_state (str): Agent's security state at time of block.

    Returns:
        Dict with status, log_id, explanation length, and fallback flag.
    """
    logger.info(
        "Generating XAI explanation for audit log %s (attempt %d/%d)",
        log_id, self.request.retries + 1, _MAX_RETRIES + 1,
    )

    try:
        explanation = _run_async(_generate_explanation_llm(payload))
    except Exception as exc:
        logger.error(
            "LLM call failed for log %s: %s", log_id, exc, exc_info=True
        )
        # On final retry, use the template fallback so the log isn't
        # stuck in pending state forever.
        if self.request.retries >= _MAX_RETRIES:
            logger.warning(
                "Max retries reached for log %s — using template fallback.",
                log_id,
            )
            explanation = _template_fallback(payload)
        else:
            raise  # Let Celery retry with exponential backoff

    # Persist the explanation to the database
    _run_async(_update_audit_log(log_id, explanation))

    logger.info(
        "XAI explanation generated for audit log %s (%d chars)",
        log_id, len(explanation),
    )

    return {
        "status": "completed",
        "log_id": log_id,
        "explanation_length": len(explanation),
        "used_fallback": not bool(GROQ_API_KEY),
    }


@shared_task(
    bind=True,
    name="workers.xai_tasks.generate_xai_batch",
    max_retries=2,
    acks_late=True,
    queue="xai",
    soft_time_limit=600,
    time_limit=660,
)
def generate_xai_batch(
    self,
    entries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Batch-generate XAI explanations for multiple audit logs.

    Useful for backfilling explanations on logs that were created while
    the XAI worker was offline, or for reprocessing failed entries.

    Args:
        entries: List of {"log_id": str, "payload": dict} objects.

    Returns:
        Dict with counts of successes and failures.
    """
    logger.info("Starting XAI batch generation for %d entries", len(entries))

    results: Dict[str, Any] = {"succeeded": 0, "failed": 0, "errors": []}

    for entry in entries:
        log_id = entry.get("log_id", "")
        payload = entry.get("payload", {})

        if not log_id:
            results["failed"] += 1
            results["errors"].append("Missing log_id in entry")
            continue

        try:
            explanation = _run_async(_generate_explanation_llm(payload))
            _run_async(_update_audit_log(log_id, explanation))
            results["succeeded"] += 1
        except Exception as exc:
            logger.error(
                "Batch XAI failed for log %s: %s", log_id, exc
            )
            # Use template fallback for failed entries so they don't
            # remain stuck in pending state
            try:
                fallback = _template_fallback(payload)
                _run_async(_update_audit_log(log_id, fallback))
                results["succeeded"] += 1
            except Exception:
                results["failed"] += 1
                results["errors"].append(f"log_id={log_id}: {str(exc)[:100]}")

    logger.info(
        "XAI batch complete: %d succeeded, %d failed",
        results["succeeded"], results["failed"],
    )
    return results


@shared_task(
    name="workers.xai_tasks.backfill_pending_xai",
    acks_late=True,
    queue="xai",
    soft_time_limit=300,
    time_limit=360,
)
def backfill_pending_xai(
    tenant_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Scan the database for audit logs with xai_pending=True and
    dispatch individual XAI generation tasks for each.

    Can be run as a periodic Celery Beat task to automatically
    recover from any dropped XAI tasks.

    Args:
        tenant_id: Optional filter — only backfill for a specific tenant.
        limit: Maximum number of pending logs to process per run.

    Returns:
        Dict with the number of tasks dispatched.
    """
    logger.info(
        "Scanning for pending XAI logs (tenant=%s, limit=%d)",
        tenant_id or "ALL", limit,
    )

    pending_logs = _run_async(_get_pending_xai_logs(tenant_id, limit))

    dispatched = 0
    for entry in pending_logs:
        generate_xai_explanation.delay(
            log_id=entry["log_id"],
            payload=entry["payload"],
        )
        dispatched += 1

    logger.info("Dispatched %d XAI generation tasks from backfill", dispatched)

    return {
        "status": "completed",
        "dispatched": dispatched,
        "scanned_tenant": tenant_id or "ALL",
    }
