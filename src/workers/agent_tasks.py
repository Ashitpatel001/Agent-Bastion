"""
workers/agent_tasks.py — Background Agent Execution Worker.

Celery task that executes the SecureAgent when triggered by the
/v1/agent/run API endpoint. This is the core of the job execution
model described in the implementation plan.

Lifecycle:
  1. API endpoint creates an AgentSession in QUEUED status.
  2. API fires `run_agent_task.delay(session_id, tenant_id)`.
  3. This worker picks up the task:
     a. Updates session to RUNNING.
     b. Instantiates SecureAgent with tenant context.
     c. Executes the agent (navigates, acts, defends).
     d. Updates session to COMPLETED (or FAILED on error).
  4. All audit logs are written by SecureAgent during execution
     (scoped to tenant_id + session_id).

Queue: 'agents' (see celery_app.py task_routes).

Concurrency notes:
  Each agent task spawns a Chromium browser instance, so concurrency
  should be kept LOW (1-2 per worker). Use -c 1 when starting workers
  dedicated to agent execution.

Usage:
    # Start agent worker (low concurrency — each task uses a browser):
    celery -A workers.celery_app worker -Q agents --loglevel=info --concurrency=1 -n agent@%h
"""

import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_task_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
AGENT_LLM_MODEL: str = os.getenv("AGENT_LLM_MODEL", "LLama")
AGENT_MAX_STEPS: int = int(os.getenv("AGENT_MAX_STEPS", "25"))


# ---------------------------------------------------------------------------
# Async ↔ Sync Bridge
# ---------------------------------------------------------------------------
def _run_async(coro):
    """
    Run an async coroutine from synchronous Celery task context.
    Creates a fresh event loop per invocation.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Database Operations
# ---------------------------------------------------------------------------
async def _update_session(
    session_id: str,
    tenant_id: str,
    status: str,
    result_summary: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Update the AgentSession status in the database.

    Uses get_db_context() (standalone context manager) since we're
    outside a FastAPI request.
    """
    from db.database import get_db_context
    from db import crud
    from db.models import SessionStatus

    async with get_db_context() as db:
        await crud.update_session_status(
            db,
            session_id=session_id,
            tenant_id=tenant_id,
            status=SessionStatus(status),
            result_summary=result_summary,
            error_message=error_message,
        )


async def _get_session_details(
    session_id: str, tenant_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch the session's task_prompt and target_url from the DB.
    """
    from db.database import get_db_context
    from db import crud

    async with get_db_context() as db:
        session = await crud.get_session(
            db, session_id=session_id, tenant_id=tenant_id
        )
        if session:
            return {
                "task_prompt": session.task_prompt,
                "target_url": session.target_url,
            }
    return None


async def _count_active_sessions(tenant_id: str) -> int:
    """
    Check how many sessions are currently QUEUED or RUNNING for a tenant.
    Used for concurrency limiting.
    """
    from db.database import get_db_context
    from db import crud

    async with get_db_context() as db:
        return await crud.count_active_sessions(db, tenant_id=tenant_id)


async def _get_tenant_max_concurrent(tenant_id: str) -> int:
    """
    Fetch the tenant's max_concurrent_sessions limit.
    """
    from db.database import get_db_context
    from db import crud

    async with get_db_context() as db:
        tenant = await crud.get_tenant_by_id(db, tenant_id=tenant_id)
        if tenant:
            return tenant.max_concurrent_sessions
    return 2  # Default fallback


# ---------------------------------------------------------------------------
# Agent Execution
# ---------------------------------------------------------------------------
async def _execute_secure_agent(
    session_id: str,
    tenant_id: str,
    task_prompt: str,
    target_url: Optional[str],
) -> str:
    """
    Instantiate and run the SecureAgent with full security layers.

    The agent is created with tenant_id and session_id so all audit
    logs and policy checks are correctly scoped.

    Returns:
        A result summary string.
    """
    from security.agent import SecureAgent

    # Build the LLM for the agent
    llm = _build_agent_llm()

    # Construct the task description
    task = task_prompt
    if target_url:
        task = f"Navigate to {target_url} and {task_prompt}"

    # Instantiate the SecureAgent with tenant context
    agent = SecureAgent(
        task=task,
        llm=llm,
        tenant_id=tenant_id,
        session_id=session_id,
    )

    # Execute the agent
    result = await agent.run(max_steps=AGENT_MAX_STEPS)

    # Extract result summary from the agent's output
    if hasattr(result, "final_result") and callable(result.final_result):
        summary = result.final_result()
        if summary:
            return str(summary)[:4000]

    if hasattr(result, "history") and result.history:
        last = result.history[-1]
        if hasattr(last, "result") and last.result:
            return str(last.result)[:4000]

    return "Agent execution completed successfully."


import os

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
AGENT_LLM_MODEL = os.getenv("AGENT_LLM_MODEL", "llama-3.3-70b-versatile")


def _build_agent_llm():
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=AGENT_LLM_MODEL,
        api_key=os.getenv("GROQ_API_KEY", ""),
    )
# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="workers.agent_tasks.run_agent_task",
    max_retries=1,
    default_retry_delay=10,
    acks_late=True,
    queue="agents",
    soft_time_limit=540,        # 9 min soft limit
    time_limit=600,             # 10 min hard kill
)
def run_agent_task(
    self,
    session_id: str,
    tenant_id: str,
) -> Dict[str, Any]:
    """
    Execute a SecureAgent job in the background.

    Triggered by the /v1/agent/run API endpoint after creating a session.
    The full agent lifecycle is managed here:
      QUEUED → RUNNING → COMPLETED / FAILED

    Args:
        session_id: The AgentSession.id to execute.
        tenant_id:  The Tenant.id that owns this session.

    Returns:
        Dict with status, session_id, and result_summary.
    """
    logger.info(
        "Starting agent task: session=%s, tenant=%s (attempt %d/%d)",
        session_id, tenant_id,
        self.request.retries + 1, 2,
    )

    # --- 0. Concurrency check ---
    try:
        max_concurrent = _run_async(_get_tenant_max_concurrent(tenant_id))
        active_count = _run_async(_count_active_sessions(tenant_id))

        # Subtract 1 because this session is already counted as QUEUED
        if active_count > max_concurrent:
            logger.warning(
                "Tenant %s exceeds concurrency limit (%d/%d). "
                "Retrying in 30 seconds.",
                tenant_id, active_count, max_concurrent,
            )
            raise self.retry(countdown=30)
    except self.MaxRetriesExceededError:
        error_msg = (
            f"Concurrency limit exceeded for tenant {tenant_id}. "
            f"Maximum {max_concurrent} concurrent sessions allowed."
        )
        _run_async(
            _update_session(
                session_id, tenant_id, "FAILED",
                error_message=error_msg,
            )
        )
        return {"status": "failed", "session_id": session_id, "error": error_msg}
    except Exception:
        pass  # Non-critical — proceed with execution

    # --- 1. Fetch session details ---
    session_details = _run_async(
        _get_session_details(session_id, tenant_id)
    )
    if not session_details:
        error_msg = f"Session {session_id} not found for tenant {tenant_id}"
        logger.error(error_msg)
        return {"status": "failed", "session_id": session_id, "error": error_msg}

    task_prompt = session_details["task_prompt"]
    target_url = session_details.get("target_url")

    # --- 2. Mark session as RUNNING ---
    _run_async(
        _update_session(session_id, tenant_id, "RUNNING")
    )

    try:
        # --- 3. Execute the SecureAgent ---
        result_summary = _run_async(
            _execute_secure_agent(
                session_id=session_id,
                tenant_id=tenant_id,
                task_prompt=task_prompt,
                target_url=target_url,
            )
        )

        # --- 4. Mark session as COMPLETED ---
        _run_async(
            _update_session(
                session_id, tenant_id, "COMPLETED",
                result_summary=result_summary[:4000] if result_summary else None,
            )
        )

        logger.info(
            "Agent task completed: session=%s (%d chars result)",
            session_id, len(result_summary or ""),
        )

        return {
            "status": "completed",
            "session_id": session_id,
            "result_summary": result_summary[:500] if result_summary else None,
        }

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {str(exc)[:500]}"
        tb = traceback.format_exc()
        logger.error(
            "Agent task failed: session=%s\n%s",
            session_id, tb,
        )

        # Mark session as FAILED
        _run_async(
            _update_session(
                session_id, tenant_id, "FAILED",
                error_message=error_msg,
            )
        )

        # Re-raise for Celery retry on first attempt
        if self.request.retries < 1:
            raise self.retry(exc=exc)

        return {
            "status": "failed",
            "session_id": session_id,
            "error": error_msg,
        }


@shared_task(
    name="workers.agent_tasks.cancel_agent_task",
    acks_late=True,
    queue="agents",
)
def cancel_agent_task(
    session_id: str,
    tenant_id: str,
) -> Dict[str, Any]:
    """
    Mark an agent session as CANCELLED.

    Note: This does NOT terminate a currently running agent — it only
    updates the DB status. True cancellation requires cooperative
    cancellation tokens in the SecureAgent (future enhancement via
    Celery revoke + AbortableTask).

    Args:
        session_id: The AgentSession.id to cancel.
        tenant_id:  The Tenant.id that owns this session.
    """
    logger.info("Cancelling agent task: session=%s", session_id)

    _run_async(
        _update_session(
            session_id, tenant_id, "CANCELLED",
            result_summary="Cancelled by user.",
        )
    )

    return {"status": "cancelled", "session_id": session_id}
