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
from typing import Any, Dict, Optional, Coroutine

from celery import shared_task
from celery.utils.log import get_task_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_task_logger(__name__)

from api.config import settings

# Constants
AGENT_LLM_MODEL: str = settings.AGENT_LLM_MODEL
AGENT_MAX_STEPS: int = settings.AGENT_MAX_STEPS

# Async ↔ Sync Bridge
def _run_async(coro: Coroutine) -> Any:
    """Utility to run an async coroutine synchronously, avoiding loop conflicts."""
    # Safest way in a thread is to use asyncio.run
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Fallback if asyncio.run fails due to existing loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# Database Operations

async def _update_session(
    session_id: str,
    tenant_id: str,
    status: str,
    result_summary: Optional[str] = None,
    error_message: Optional[str] = None,
    celery_task_id: Optional[str] = None,
) -> None:
    """
    Update the AgentSession status and lifecycle events in the database.
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
            celery_task_id=celery_task_id,
        )


async def _get_session_details(
    session_id: str, tenant_id: str
) -> Optional[Dict[str, Any]]:
    """
    Fetch the session's task_prompt, target_url, user_id, and retry settings from the DB.
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
                "user_id": session.user_id,
                "max_retries": session.max_retries if session.max_retries is not None else 3,
                "celery_task_id": session.celery_task_id,
            }
    return None


def _check_memory_usage(threshold_percent: float = 92.0) -> bool:
    """
    Resource protection hook (Task 4.5): Check if system virtual memory is within safe limits.
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        if mem.percent > threshold_percent:
            logger.warning("High system memory usage threshold reached: %f%% > %f%%", mem.percent, threshold_percent)
            return False
    except ImportError:
        pass
    return True


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
    return 2 

# Agent Execution
def _extract_agent_summary(result) -> str:
    """Dynamically extracts clean human-readable results, items, and summaries from agent execution history."""
    extracted_data = []
    actions_taken = []
    final_text = None

    # 1. Check if final_result() produced clean text
    if hasattr(result, "final_result") and callable(result.final_result):
        res = result.final_result()
        if res and isinstance(res, str) and res.strip() and not res.strip().startswith("[ActionResult"):
            final_text = res.strip()

    # 2. Iterate through step history to collect extracted items and memory
    if hasattr(result, "history") and result.history:
        for idx, step in enumerate(result.history, 1):
            # Collect extracted content from actions
            if hasattr(step, "result") and step.result:
                for ar in step.result:
                    if hasattr(ar, "extracted_content") and ar.extracted_content:
                        content_str = str(ar.extracted_content).strip()
                        if content_str and content_str not in extracted_data:
                            extracted_data.append(content_str)
                    if hasattr(ar, "error") and ar.error and "Security Block" in str(ar.error):
                        actions_taken.append(f"⚠️ Security interception: {ar.error}")

            # Collect model planning / memory
            if hasattr(step, "model_output") and step.model_output:
                mo = step.model_output
                if hasattr(mo, "current_state") and mo.current_state:
                    cs = mo.current_state
                    if hasattr(cs, "memory") and cs.memory and cs.memory not in actions_taken:
                        actions_taken.append(str(cs.memory))
                    if hasattr(cs, "evaluation_previous_goal") and cs.evaluation_previous_goal:
                        eval_str = str(cs.evaluation_previous_goal)
                        if "success" in eval_str.lower() or "found" in eval_str.lower():
                            if eval_str not in actions_taken:
                                actions_taken.append(eval_str)

    # Build formatted markdown output
    sections = []
    if final_text:
        sections.append(f"### Mission Output\n{final_text}")

    if extracted_data:
        sections.append("### Extracted Items & Findings")
        for i, item in enumerate(extracted_data, 1):
            sections.append(f"{i}. {item}")

    if actions_taken and not final_text and not extracted_data:
        sections.append("### Execution Log Summary")
        for act in actions_taken[-5:]:
            sections.append(f"- {act}")

    if not sections:
        step_count = len(result.history) if hasattr(result, "history") and result.history else 0
        return f"Autonomous agent navigated target environment and completed mission over {step_count} step(s)."

    return "\n\n".join(sections)[:4000]


async def _execute_secure_agent(
    session_id: str,
    tenant_id: str,
    task_prompt: str,
    target_url: Optional[str] = None,
) -> str:
    """
    Instantiate and run a SecureAgent inside an async coroutine.

    Ensures the async DB logger is active in the current loop so that
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

    async def _add_telemetry(session_id, tenant_id, event_data):
        from db.database import get_db_context
        from db.crud import add_telemetry_event
        async with get_db_context() as db:
            await add_telemetry_event(db, session_id, tenant_id, event_data)
            await db.commit()

    async def step_callback(state, agent_output, step_num):
        msg = f"Executing step {step_num}..."
        try:
            if hasattr(agent_output, "current_state") and agent_output.current_state:
                cs = agent_output.current_state
                if hasattr(cs, "next_goal") and cs.next_goal:
                    msg = cs.next_goal
                elif hasattr(cs, "memory") and cs.memory:
                    msg = cs.memory
                
            # Log navigation if present
            if hasattr(agent_output, "action") and agent_output.action:
                for act in agent_output.action:
                    if hasattr(act, "navigate") and act.navigate:
                        msg = f"Navigating to {act.navigate.url}"
                        break
        except Exception:
            pass

        event = {
            "type": "step",
            "step_num": step_num,
            "message": msg
        }
        await _add_telemetry(session_id, tenant_id, event)

    # Instantiate the SecureAgent with tenant context
    agent = SecureAgent(
        task=task,
        llm=llm,
        tenant_id=tenant_id,
        session_id=session_id,
        register_new_step_callback=step_callback,
    )

    # Log initialization
    await _add_telemetry(session_id, tenant_id, {"type": "system", "message": "Session Created"})
    await _add_telemetry(session_id, tenant_id, {"type": "system", "message": "Browser Started"})
    
    # Execute the agent
    result = await agent.run(max_steps=AGENT_MAX_STEPS)
    
    await _add_telemetry(session_id, tenant_id, {"type": "system", "message": "Mission Completed"})

    # Extract dynamic human-readable summary
    return _extract_agent_summary(result)


LLM_PROVIDER = settings.LLM_PROVIDER.lower()
AGENT_LLM_MODEL = settings.AGENT_LLM_MODEL


def _build_agent_llm():
    if settings.PRIMARY_LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=settings.OPENAI_MODEL if hasattr(settings, "OPENAI_MODEL") else "gpt-4o", api_key=settings.OPENAI_API_KEY)
        object.__setattr__(llm, "provider", "openai")
        return llm
    
    if settings.PRIMARY_LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model=settings.AGENT_LLM_MODEL, google_api_key=settings.GEMINI_API_KEY)
        object.__setattr__(llm, "provider", "google")
        return llm

    if settings.PRIMARY_LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq
        from langchain_core.language_models.chat_models import BaseChatModel
        
        # Ensure compatibility with browser-use checks and telemetry wrapper registrations
        for cls in (ChatGroq, BaseChatModel):
            if not hasattr(cls, "_browser_use_patched"):
                orig_setattr = cls.__setattr__
                def permissive_setattr(self, name, val):
                    try:
                        orig_setattr(self, name, val)
                    except ValueError:
                        object.__setattr__(self, name, val)
                cls.__setattr__ = permissive_setattr
                cls._browser_use_patched = True

        if not hasattr(ChatGroq, "provider"):
            ChatGroq.provider = "groq"

        llm = ChatGroq(
            model=settings.AGENT_LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
        )
        object.__setattr__(llm, "provider", "groq")
        return llm

    # If no provider is configured, we must raise an explicit exception
    raise ValueError("No valid LLM provider configured! Please set GEMINI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY in your .env file.")

# Celery Tasks

@shared_task(
    bind=True,
    name="workers.agent_tasks.run_agent_task",
    max_retries=settings.MAX_RETRIES,
    default_retry_delay=15,
    acks_late=True,
    queue="agents",
    soft_time_limit=settings.MAX_BROWSER_RUNTIME_SECONDS,
    time_limit=settings.WORKER_TIMEOUT_SECONDS,
)
def run_agent_task(
    self,
    session_id: str,
    tenant_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a SecureAgent job with full Phase 4 orchestration and resource protection.
    """
    retries = getattr(self.request, "retries", 0) if hasattr(self, "request") else 0
    celery_task_id = getattr(self.request, "id", None) if hasattr(self, "request") else None
    logger.info(
        "Starting agent task: session=%s, tenant=%s, user=%s (attempt %d/max)",
        session_id, tenant_id, user_id or "NONE",
        retries + 1,
    )

    # --- 0. Memory & Concurrency Check (Task 4.5) ---
    if not _check_memory_usage(threshold_percent=92.0):
        logger.warning("Worker memory critical. Deferring task %s by 30 seconds.", session_id)
        if hasattr(self, "retry"):
            try:
                raise self.retry(countdown=30)
            except self.MaxRetriesExceededError:
                pass

    try:
        max_concurrent = _run_async(_get_tenant_max_concurrent(tenant_id))
        active_count = _run_async(_count_active_sessions(tenant_id))

        if active_count > max_concurrent:
            logger.warning(
                "Tenant %s exceeds concurrency limit (%d/%d). Retrying in 30 seconds.",
                tenant_id, active_count, max_concurrent,
            )
            if hasattr(self, "retry"):
                raise self.retry(countdown=30)
    except Exception as exc:
        if type(exc).__name__ == "MaxRetriesExceededError":
            error_msg = f"Concurrency limit exceeded for tenant {tenant_id}. Max {max_concurrent} allowed."
            _run_async(_update_session(session_id, tenant_id, "FAILED", error_message=error_msg, celery_task_id=celery_task_id))
            return {"status": "failed", "session_id": session_id, "error": error_msg}

    # --- 1. Fetch session details ---
    import time
    session_details = None
    for _attempt in range(5):
        session_details = _run_async(_get_session_details(session_id, tenant_id))
        if session_details:
            break
        time.sleep(0.3)

    if not session_details:
        error_msg = f"Session {session_id} not found for tenant {tenant_id}"
        logger.error(error_msg)
        try:
            _run_async(_update_session(session_id, tenant_id, "FAILED", error_message=error_msg))
        except Exception:
            pass
        return {"status": "failed", "session_id": session_id, "error": error_msg}

    task_prompt = session_details["task_prompt"]
    target_url = session_details.get("target_url")
    max_retries_allowed = session_details.get("max_retries", 3)

    # --- 2. Mark session as RUNNING ---
    _run_async(
        _update_session(session_id, tenant_id, "RUNNING", celery_task_id=celery_task_id)
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
                celery_task_id=celery_task_id,
            )
        )

        logger.info("Agent task completed: session=%s (%d chars result)", session_id, len(result_summary or ""))
        return {
            "status": "completed",
            "session_id": session_id,
            "result_summary": result_summary[:500] if result_summary else None,
        }

    except Exception as exc:
        exc_type = type(exc).__name__
        tb = traceback.format_exc()
        is_timeout = "TimeLimitExceeded" in exc_type or "TimeoutError" in exc_type

        if is_timeout:
            error_msg = f"Task timed out after reaching time limit: {exc_type}"
            logger.error("Agent task timed out: session=%s\n%s", session_id, tb)
            _run_async(_update_session(session_id, tenant_id, "TIMED_OUT", error_message=error_msg, celery_task_id=celery_task_id))
            return {"status": "timed_out", "session_id": session_id, "error": error_msg}

        if hasattr(self, "retry") and retries < max_retries_allowed:
            countdown = min(300, 15 * (2 ** retries))
            logger.warning("Agent task failed (%s). Retrying in %ds (attempt %d/%d)...", exc_type, countdown, retries + 1, max_retries_allowed)
            _run_async(_update_session(session_id, tenant_id, "RETRYING", error_message=f"Retrying ({retries+1}/{max_retries_allowed}): {str(exc)[:200]}", celery_task_id=celery_task_id))
            try:
                raise self.retry(exc=exc, countdown=countdown)
            except getattr(self, "MaxRetriesExceededError", Exception):
                pass

        # Dead-letter handling for terminal failure (Task 4.3)
        error_msg = f"Dead-letter task failure [{exc_type}]: {str(exc)[:400]}"
        logger.error("Agent task terminal failure (dead-letter): session=%s\n%s", session_id, tb)
        _run_async(_update_session(session_id, tenant_id, "FAILED", error_message=error_msg, celery_task_id=celery_task_id))

        return {
            "status": "failed",
            "session_id": session_id,
            "error": error_msg,
            "dead_letter": True,
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
    Mark an agent session as CANCELLED and actively revoke/terminate running Celery worker task.
    """
    logger.info("Cancelling agent task: session=%s", session_id)

    session_details = _run_async(_get_session_details(session_id, tenant_id))
    if session_details and session_details.get("celery_task_id"):
        try:
            from workers.celery_app import celery_app
            celery_app.control.revoke(session_details["celery_task_id"], terminate=True, signal="SIGTERM")
            logger.info("Sent Celery revoke (SIGTERM) for task %s", session_details["celery_task_id"])
        except Exception as e:
            logger.warning("Failed to revoke Celery task: %s", e)

    _run_async(
        _update_session(
            session_id, tenant_id, "CANCELLED",
            result_summary="Cancelled by user.",
        )
    )

    return {"status": "cancelled", "session_id": session_id}
