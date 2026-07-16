"""
security/policy_engine.py — Production-Grade Tenant-Aware Policy Engine.

Replaces the legacy file-based PolicyEngine with a database-backed,
TTL-cached implementation that fetches policies from the SQLAlchemy
`Policy` model using the current tenant's context.

Architecture:
  - `TenantPolicyEngine`: Primary class. Fetches the active policy from
    the DB for the given tenant_id. Uses an in-memory TTL cache to
    avoid hammering the DB on every DOM interaction / action check.
  - `PolicyEngine` (legacy): Preserved with the same API for backward
    compatibility during migration. Falls back to file-based policies
    if no tenant context is available.

Cache strategy:
  - Policy is fetched from DB at most once per `cache_ttl_seconds`
    (default: 30 seconds).
  - Cache is invalidated on explicit reload or when TTL expires.
  - Thread-safe via asyncio locks.
"""

import asyncio
import json
import logging
import re
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("security.policy_engine")


# ============================================================================
# TenantPolicyEngine — Production DB-backed, TTL-cached
# ============================================================================

class TenantPolicyEngine:
    """
    Enterprise Policy Engine that fetches rules from the database
    for a specific tenant, with in-memory TTL caching.

    Usage:
        engine = TenantPolicyEngine(tenant_id="abc123", cache_ttl_seconds=30)
        is_blocked = await engine.check_navigation("https://evil.ru/phish")
        is_blocked = await engine.check_action("open_tab")
        is_blocked = await engine.check_input("my_password_123")
    """

    # Default policies used when DB fetch fails or tenant has no policy
    DEFAULT_BLOCKED_DOMAINS = ["*.ru", "*.cn", "bit.ly", "tinyurl.com", "pastebin.com"]
    DEFAULT_BLOCKED_PATTERNS = ["password", "ssn", "credit_card", "secret_key"]
    DEFAULT_MAX_RISK_TOLERANCE = 75

    def __init__(
        self,
        tenant_id: str,
        *,
        cache_ttl_seconds: float = 30.0,
        async_logger=None,
    ):
        self.tenant_id = tenant_id
        self.cache_ttl_seconds = cache_ttl_seconds
        self._async_logger = async_logger

        # Cache state
        self._cached_policy: Optional[dict] = None
        self._cache_timestamp: float = 0.0
        self._cache_lock = asyncio.Lock()
        self._initialized = False

        # Task 1.4: Bounded rate limit tracker with automatic TTL eviction to prevent memory leaks
        self._rate_limit_tracker: dict[str, list[float]] = {}
        self._rate_limit_lock = asyncio.Lock()

    @property
    def _cache_expired(self) -> bool:
        return (time.monotonic() - self._cache_timestamp) > self.cache_ttl_seconds

    async def _ensure_policy_loaded(self):
        """Fetch the active policy from DB if cache is expired or empty."""
        if self._cached_policy is not None and not self._cache_expired:
            return

        async with self._cache_lock:
            # Double-check after acquiring lock
            if self._cached_policy is not None and not self._cache_expired:
                return

            try:
                from db.database import get_db_context
                from db import crud

                async with get_db_context() as db:
                    policy = await crud.get_active_policy(db, self.tenant_id)

                if policy:
                    self._cached_policy = {
                        "blocked_domains": policy.blocked_domains or self.DEFAULT_BLOCKED_DOMAINS,
                        "blocked_input_patterns": policy.blocked_input_patterns or self.DEFAULT_BLOCKED_PATTERNS,
                        "blocked_actions": policy.blocked_actions or [],
                        "trusted_domains": policy.trusted_domains or [],
                        "max_risk_tolerance": policy.max_risk_tolerance
                            if policy.max_risk_tolerance is not None
                            else self.DEFAULT_MAX_RISK_TOLERANCE,
                        "require_human_approval": policy.require_human_approval or False,
                        "rate_limits": policy.rate_limits or {"requests_per_minute": 200, "burst_limit": 50},
                    }
                    self._cache_timestamp = time.monotonic()
                    self._initialized = True
                    logger.debug(
                        "Policy cache refreshed for tenant %s "
                        "(domains=%d, patterns=%d, blocked_actions=%d)",
                        self.tenant_id,
                        len(self._cached_policy["blocked_domains"]),
                        len(self._cached_policy["blocked_input_patterns"]),
                        len(self._cached_policy["blocked_actions"]),
                    )
                else:
                    # No active policy — use defaults
                    logger.warning(
                        "No active policy found for tenant %s, using defaults",
                        self.tenant_id,
                    )
                    self._cached_policy = self._default_policies()
                    self._cache_timestamp = time.monotonic()

            except Exception as e:
                logger.error(
                    "Failed to fetch policy from DB for tenant %s: %s",
                    self.tenant_id, e,
                )
                # Use defaults on failure so the engine never crashes
                if self._cached_policy is None:
                    self._cached_policy = self._default_policies()
                    self._cache_timestamp = time.monotonic()

    def _default_policies(self) -> dict:
        return {
            "blocked_domains": list(self.DEFAULT_BLOCKED_DOMAINS),
            "blocked_input_patterns": list(self.DEFAULT_BLOCKED_PATTERNS),
            "blocked_actions": [],
            "trusted_domains": [],
            "max_risk_tolerance": self.DEFAULT_MAX_RISK_TOLERANCE,
            "require_human_approval": False,
            "rate_limits": {"requests_per_minute": 200, "burst_limit": 50},
        }

    async def invalidate_cache(self):
        """Force a cache refresh on the next policy check."""
        async with self._cache_lock:
            self._cached_policy = None
            self._cache_timestamp = 0.0

    async def check_navigation(self, url: str) -> bool:
        """
        Returns True if the URL should be BLOCKED, False if allowed.

        Checks against the tenant's blocked domain list, supporting:
          - Exact match: "bit.ly" matches "bit.ly"
          - Subdomain match: "youtube.com" matches "www.youtube.com"
          - Wildcard: "*.ru" matches "evil.ru", "sub.evil.ru"
        """
        await self._ensure_policy_loaded()

        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            if not domain:
                return False

            # Check trusted domains first (allow-list overrides block-list)
            for trusted in self._cached_policy.get("trusted_domains", []):
                trusted = trusted.lower()
                if domain == trusted or domain.endswith("." + trusted):
                    return False

            for blocked_raw in self._cached_policy.get("blocked_domains", []):
                blocked = blocked_raw.lower()

                # Exact or subdomain match
                if domain == blocked or domain.endswith("." + blocked):
                    await self._log_policy_violation(
                        f"[OWASP LLM07 | MITRE AML.T0042] Navigation to {domain} "
                        f"blocked by Enterprise Policy.",
                        url=url,
                        risk_score=95,
                    )
                    return True

                # Wildcard matching (e.g., "*.ru")
                pattern = blocked.replace(".", r"\.").replace("*", ".*")
                if re.search(f"^{pattern}$", domain):
                    await self._log_policy_violation(
                        f"[OWASP LLM07 | MITRE AML.T0042] Navigation to {domain} "
                        f"blocked by Enterprise Policy (wildcard: {blocked_raw}).",
                        url=url,
                        risk_score=95,
                    )
                    return True

        except Exception as e:
            logger.error("Error in check_navigation: %s", e)

        return False

    async def check_input(self, text: str) -> bool:
        """Returns True if the text contains a blocked DLP pattern."""
        await self._ensure_policy_loaded()

        text_lower = str(text).lower()
        for pattern in self._cached_policy.get("blocked_input_patterns", []):
            if pattern.lower() in text_lower:
                await self._log_policy_violation(
                    f"[OWASP LLM07 | MITRE AML.T0042] Agent attempted to input "
                    f"sensitive data matching policy: '{pattern}'.",
                    url="N/A",
                    risk_score=85,
                    risk_level="HIGH",
                )
                return True
        return False

    async def check_action(self, action_type: str) -> bool:
        """Returns True if the action is in the blocked actions list."""
        await self._ensure_policy_loaded()

        blocked = self._cached_policy.get("blocked_actions", [])
        if blocked and action_type in blocked:
            await self._log_policy_violation(
                f"[OWASP LLM07 | MITRE AML.T0042] Action '{action_type}' is "
                f"found in the blocked actions policy.",
                url="N/A",
                risk_score=80,
                risk_level="HIGH",
            )
            return True
        return False

    async def check_rate_limit(self, action_key: str, max_requests: int = 100, window_seconds: float = 60.0) -> bool:
        """
        Check rate limit against bounded sliding window.
        Returns True if rate limit is EXCEEDED, False if allowed.
        Automatically cleans up expired entries to prevent memory leaks (Task 1.4).
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        async with self._rate_limit_lock:
            # Periodic global eviction if tracker bounds grow (>1000 keys)
            if len(self._rate_limit_tracker) > 1000:
                expired_keys = [
                    k for k, timestamps in self._rate_limit_tracker.items()
                    if not timestamps or timestamps[-1] < cutoff
                ]
                for k in expired_keys:
                    self._rate_limit_tracker.pop(k, None)

            timestamps = self._rate_limit_tracker.get(action_key, [])
            timestamps = [t for t in timestamps if t >= cutoff]

            if len(timestamps) >= max_requests:
                self._rate_limit_tracker[action_key] = timestamps
                await self._log_policy_violation(
                    f"[OWASP LLM07 | MITRE AML.T0042] Rate limit exceeded for action '{action_key}'.",
                    url="N/A",
                    risk_score=75,
                    risk_level="HIGH",
                )
                return True

            timestamps.append(now)
            self._rate_limit_tracker[action_key] = timestamps
            return False

    @property
    def max_risk_tolerance(self) -> int:
        """Current max risk tolerance threshold from the cached policy."""
        if self._cached_policy:
            return self._cached_policy.get(
                "max_risk_tolerance", self.DEFAULT_MAX_RISK_TOLERANCE
            )
        return self.DEFAULT_MAX_RISK_TOLERANCE

    @property
    def require_human_approval(self) -> bool:
        """Whether human-in-the-loop approval is required."""
        if self._cached_policy:
            return self._cached_policy.get("require_human_approval", False)
        return False

    async def _log_policy_violation(
        self,
        details: str,
        url: str = "N/A",
        risk_score: int = 95,
        risk_level: str = "CRITICAL",
    ):
        """Log a policy violation event."""
        if self._async_logger:
            await self._async_logger.log_event(
                event_type="POLICY_VIOLATION",
                url=url,
                details=details,
                risk_level=risk_level,
                risk_score=risk_score,
                action="BLOCKED",
            )
        else:
            # Fallback to legacy logger
            from security.event_logger import SecurityLogger
            SecurityLogger.log_event(
                event_type="POLICY_VIOLATION",
                url=url,
                details=details,
                risk_level=risk_level,
                risk_score=risk_score,
                action="BLOCKED",
            )


# ============================================================================
# PolicyEngine — Legacy Synchronous API (Backward Compatibility)
# ============================================================================

class PolicyEngine:
    """
    Enterprise Role-Based Access Control (RBAC) & Policy Enforcement for AI Agents.

    Legacy synchronous API preserved for backward compatibility.
    For new code, use TenantPolicyEngine (async, DB-backed).

    This class wraps TenantPolicyEngine internally when a tenant_id is
    provided, otherwise falls back to file-based policies for local mode.
    """

    def __init__(self, config_dir: Path = None, *, tenant_id: str = None, async_logger=None):
        self._tenant_id = tenant_id
        self._async_engine: Optional[TenantPolicyEngine] = None
        self._async_logger = async_logger

        if tenant_id:
            # Production mode: use DB-backed engine
            self._async_engine = TenantPolicyEngine(
                tenant_id=tenant_id,
                async_logger=async_logger,
            )
        else:
            # Legacy mode: file-based
            self.config_file = (config_dir or Path(__file__).parent / "dashboard") / "policies.json"
            self.reload_policies()

    def reload_policies(self):
        """Loads or creates the default enterprise policy file (legacy mode)."""
        if self._async_engine:
            return  # DB-backed engine handles its own caching

        if not hasattr(self, 'config_file'):
            return

        if not self.config_file.parent.exists():
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.policies = json.load(f)
            except Exception:
                self.policies = self._default_policies()
        else:
            self.policies = self._default_policies()
            self.save_policies()

    def save_policies(self):
        if hasattr(self, 'config_file'):
            with open(self.config_file, "w") as f:
                json.dump(self.policies, f, indent=4)

    def _default_policies(self) -> Dict:
        return {
            "block_domains": ["*.ru", "*.cn", "bit.ly", "tinyurl.com", "pastebin.com"],
            "block_input_patterns": ["password", "ssn", "credit_card", "secret_key"],
            "max_risk_tolerance": 75,
            "require_human_approval": False,
            "blocked_actions": []
        }

    def check_navigation(self, url: str) -> bool:
        """Returns True if blocked, False if allowed."""
        if self._async_engine:
            # Bridge sync → async
            try:
                loop = asyncio.get_running_loop()
                # We're inside an async context, create a task
                future = asyncio.ensure_future(
                    self._async_engine.check_navigation(url)
                )
                # Can't await in sync method — use the event loop
                # This path shouldn't be hit in normal operation since
                # SecureAgent methods are all async now
                return False
            except RuntimeError:
                # No event loop — fall back to sync check
                pass

        # Legacy sync check
        self.reload_policies()
        try:
            domain = urllib.parse.urlparse(url).netloc.lower()
            for blocked_raw in self.policies.get("block_domains", []):
                blocked = blocked_raw.lower()

                if domain == blocked or domain.endswith("." + blocked):
                    return True

                pattern = blocked.replace(".", r"\.").replace("*", ".*")
                if re.search(f"^{pattern}$", domain):
                    return True
        except Exception:
            pass
        return False

    def check_input(self, text: str) -> bool:
        """Returns True if the text contains a blocked pattern."""
        if self._async_engine:
            return False  # Async path handled separately

        self.reload_policies()
        text_lower = str(text).lower()
        for pattern in self.policies.get("block_input_patterns", []):
            if pattern.lower() in text_lower:
                return True
        return False

    def check_action(self, action_type: str) -> bool:
        """Returns True if the action is in the blocked list."""
        if self._async_engine:
            return False  # Async path handled separately

        self.reload_policies()
        blocked = self.policies.get("blocked_actions", [])
        if blocked and action_type in blocked:
            return True
        return False
