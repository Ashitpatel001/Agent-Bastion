"""
security/event_logger.py — Production-Grade Async Security Event Logger.

Replaces the legacy file-lock JSONL approach with async database inserts
via SQLAlchemy. This is the single chokepoint for all security telemetry
in the engine — every DOM scan, action block, and XAI explanation flows
through here.

Architecture:
  - `AsyncSecurityLogger`: The primary class. Requires a tenant_id and
    optional session_id. All writes go to the `audit_logs` table via the
    CRUD layer.
  - `SecurityLogger` (legacy): Static methods preserved for backward
    compatibility during migration. Delegates to JSONL file if no tenant
    context is available, or queues an async DB insert if a global tenant
    context is set.

Migration path:
  1. SecureAgent now creates an AsyncSecurityLogger and passes it around.
  2. Old SecurityLogger.log_event calls still work for any code that
     hasn't been refactored yet (e.g., reputation.py, deception.py).
  3. Once all callers migrate, SecurityLogger can be removed.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("security.event_logger")

# ---------------------------------------------------------------------------
# Legacy file paths (kept for backward compat & non-tenant local mode)
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).parent / "dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = OUTPUT_DIR / "security_events.jsonl"
SCREENSHOTS_DIR = OUTPUT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# AsyncSecurityLogger — Production DB-backed logger
# ============================================================================

class AsyncSecurityLogger:
    """
    Async, database-backed security event logger for multi-tenant operation.

    Each instance is scoped to a single tenant + session, injected at
    SecureAgent construction time. All writes are non-blocking async
    inserts via SQLAlchemy.

    Usage:
        logger = AsyncSecurityLogger(tenant_id="abc123", session_id="sess456")
        await logger.log_event(
            event_type="INJECTION_ATTEMPT",
            url="https://evil.com",
            details="Blocked prompt injection",
            risk_level="CRITICAL",
            risk_score=95,
            action="SANITIZED",
        )
    """

    def __init__(
        self,
        tenant_id: str,
        session_id: Optional[str] = None,
        *,
        write_jsonl_fallback: bool = True,
    ):
        self.tenant_id = tenant_id
        self.session_id = session_id
        self._write_jsonl_fallback = write_jsonl_fallback
        self._log_buffer: list = []
        self._flush_lock = asyncio.Lock()

    async def log_event(
        self,
        event_type: str,
        url: str = "",
        details: str = "",
        risk_level: str = "LOW",
        risk_score: int = 0,
        action: str = "ALLOWED",
        screenshot_path: Optional[str] = None,
        explanation: Optional[str] = None,
        risk_breakdown: Optional[dict] = None,
        xai_pending: bool = False,
    ) -> Optional[str]:
        """
        Insert a security event into the database.

        Returns:
            The audit log ID on success, None on failure.
        """
        # Normalize action name to match DB enum values
        action_taken = self._normalize_action(action)

        try:
            from db.database import get_db_context
            from db.schemas import AuditLogCreate
            from db import crud

            log_data = AuditLogCreate(
                tenant_id=self.tenant_id,
                session_id=self.session_id,
                event_type=event_type,
                url=url or "",
                details=details,
                risk_level=risk_level,
                risk_score=min(max(risk_score, 0), 100),
                action_taken=action_taken,
                risk_breakdown=risk_breakdown,
                screenshot_path=screenshot_path,
                xai_explanation=explanation,
                xai_pending=xai_pending,
            )

            async with get_db_context() as db:
                audit_log = await crud.create_audit_log(db, log_data)
                log_id = audit_log.id
                logger.debug(
                    "Audit log %s created (tenant=%s, type=%s, risk=%d)",
                    log_id, self.tenant_id, event_type, risk_score,
                )
                return log_id

        except Exception as e:
            logger.error("Failed to write audit log to DB: %s", e, exc_info=True)

            # Fallback: write to JSONL so no event is ever lost
            if self._write_jsonl_fallback:
                self._write_jsonl_entry(
                    event_type=event_type,
                    url=url,
                    details=details,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    action=action,
                    screenshot_path=screenshot_path,
                    explanation=explanation,
                )
            return None

    async def update_xai_explanation(
        self, log_id: str, explanation: str
    ) -> bool:
        """
        Backfill an XAI explanation for an existing audit log entry.
        Called after async XAI generation completes.
        """
        try:
            from db.database import get_db_context
            from db import crud

            async with get_db_context() as db:
                success = await crud.update_audit_xai_explanation(
                    db, log_id, explanation
                )
                if success:
                    logger.debug("XAI explanation backfilled for log %s", log_id)
                return success

        except Exception as e:
            logger.error("Failed to update XAI explanation: %s", e)
            return False

    @staticmethod
    def _normalize_action(action: str) -> str:
        """Map legacy action strings to DB enum values."""
        action_map = {
            "BLOCKED": "BLOCKED",
            "SANITIZED": "SANITIZED",
            "WARNED": "WARNED",
            "ALLOWED": "ALLOWED",
            "MONITOR": "MONITOR",
            "EXPLAINED": "EXPLAINED",
            "BLOCK_AND_ESCALATE": "BLOCK_AND_ESCALATE",
            # Legacy aliases
            "AUTO_APPROVE": "ALLOWED",
        }
        return action_map.get(action.upper(), "ALLOWED")

    @staticmethod
    def _write_jsonl_entry(**kwargs):
        """Fallback JSONL writer — used when DB is unavailable."""
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            **kwargs,
        }
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error("JSONL fallback write failed: %s", e)

    @staticmethod
    def get_screenshot_dir() -> Path:
        return SCREENSHOTS_DIR


# ============================================================================
# SecurityLogger — Legacy Static API (Backward Compatibility)
# ============================================================================

class SecurityLogger:
    """
    Legacy static logger for backward compatibility.

    Code that hasn't been migrated to AsyncSecurityLogger can still call
    SecurityLogger.log_event(...) synchronously. Events are written to
    JSONL and optionally queued for async DB insert if a global tenant
    context is available.

    This class will be removed once all callers migrate to
    AsyncSecurityLogger.
    """

    # Global tenant context — set by SecureAgent.__init__ so that
    # unmigrated callers (e.g., PolicyEngine, ReputationManager) can
    # still have their events routed to the DB.
    _global_async_logger: Optional[AsyncSecurityLogger] = None

    @classmethod
    def set_global_context(cls, async_logger: AsyncSecurityLogger):
        """Set the global async logger for legacy callers."""
        cls._global_async_logger = async_logger

    @classmethod
    def clear_global_context(cls):
        """Clear the global async logger context."""
        cls._global_async_logger = None

    @staticmethod
    def log_event(
        event_type: str,
        url: str,
        details: str,
        risk_level: str,
        action: str,
        screenshot_path: str = None,
        risk_score: int = 0,
        explanation: str = None,
    ):
        """
        Logs a structured security event.

        If a global async logger is set, events are dispatched to the DB
        via fire-and-forget async task. Otherwise, falls back to JSONL.
        """
        # Always write to JSONL for immediate local availability
        entry = {
            "timestamp": time.time(),
            "time_str": time.strftime("%H:%M:%S"),
            "event_type": event_type,
            "url": url,
            "details": details,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "action": action,
            "screenshot": screenshot_path,
            "explanation": explanation,
        }

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to write security log: %s", e)

        # If global async logger is available, also queue DB write
        if SecurityLogger._global_async_logger is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    SecurityLogger._global_async_logger.log_event(
                        event_type=event_type,
                        url=url,
                        details=details,
                        risk_level=risk_level,
                        risk_score=risk_score,
                        action=action,
                        screenshot_path=screenshot_path,
                        explanation=explanation,
                    )
                )
            except RuntimeError:
                # No running event loop — skip async dispatch
                pass

    @staticmethod
    def get_screenshot_dir():
        return SCREENSHOTS_DIR

    @staticmethod
    def clear_logs():
        if LOG_FILE.exists():
            os.remove(LOG_FILE)
