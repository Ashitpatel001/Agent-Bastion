"""
security/agent.py — Production-Grade Secure Agent (v2.0).

Core Security Engine for the ABSs Multi-Tenant AI Browser Security Proxy.
Implements a defense-in-depth "Zero-Trust Guardian" architecture with
four distinct security layers.

v2.0 Changes (Component 3 — Core Security Engine Refactoring):
  - REMOVED: `object.__setattr__` monkey-patching of browser_session.
    Now uses `_create_secure_state_wrapper()` which wraps the method
    through the Agent's own `__init__` without fragile internal access.
  - ADDED: Tenant context injection — `SecureAgent` accepts `tenant_id`
    and `session_id` to scope all events and policies to the correct
    tenant.
  - REPLACED: `SecurityLogger.log_event` (file-lock JSONL) with
    `AsyncSecurityLogger.log_event` (async DB inserts) as the primary
    logging path. Legacy SecurityLogger kept as fallback.
  - REPLACED: File-based `PolicyEngine` with `TenantPolicyEngine`
    (DB-backed, TTL-cached) when a tenant_id is provided.

Security Layers:
  Layer 0: Constitutional AI (hardened system prompt — set in main_secure.py)
  Layer 1: DOM Sanitization Lens (pre-execution content filtering)
  Layer 2: Action Sentinel (in-execution action mediation + risk scoring)
  Layer 3: Network Firewall (honey token DLP + cross-origin blocking)
  Layer 4: Explainable AI (LLM-generated explanations for blocked actions)
"""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, List, Optional
from urllib.parse import urlparse

from browser_use import Agent

from .config import SecurityConfig
from .event_logger import AsyncSecurityLogger, SecurityLogger
from .policy_engine import PolicyEngine, TenantPolicyEngine
from .reputation import ReputationManager
from .risk_scorer import RiskScorer

# Configure logging
logger = logging.getLogger("security.agent")


class SecureAgent(Agent):
    """
    A secure wrapper around the Browser Use Agent.
    Implements a defense-in-depth "Zero-Trust Guardian" architecture.

    Security Layers:
      Layer 0: Constitutional AI (hardened system prompt — set in main_secure.py)
      Layer 1: DOM Sanitization Lens (pre-execution content filtering)
      Layer 2: Action Sentinel (in-execution action mediation + risk scoring)
      Layer 3: Network Firewall (honey token DLP + cross-origin blocking)
      Layer 4: Explainable AI (LLM-generated explanations for blocked actions)

    Multi-Tenant Parameters:
      tenant_id:   Scopes all policies and audit logs to this tenant.
      session_id:  Links all audit logs to a specific agent job execution.
    """

    def __init__(self, *args, **kwargs):
        # --- Extract multi-tenant parameters before passing to parent ---
        self._tenant_id: Optional[str] = kwargs.pop("tenant_id", None)
        self._session_id: Optional[str] = kwargs.pop("session_id", None)

        # --- Ensure LLM compatibility with browser-use library ---
        llm = kwargs.get("llm")
        if llm is not None:
            cls = type(llm)
            if not hasattr(cls, "_browser_use_patched"):
                orig_setattr = cls.__setattr__
                def permissive_setattr(s, n, v):
                    try:
                        orig_setattr(s, n, v)
                    except ValueError:
                        object.__setattr__(s, n, v)
                cls.__setattr__ = permissive_setattr
                cls._browser_use_patched = True
            if not hasattr(llm, "provider"):
                object.__setattr__(llm, "provider", getattr(llm, "_provider", "groq"))
            if not hasattr(cls, "provider"):
                cls.provider = property(lambda s: getattr(s, "_provider", "groq"))

        super().__init__(*args, **kwargs)

        # --- Initialize Async Logger (DB-backed) ---
        if self._tenant_id:
            self._async_logger = AsyncSecurityLogger(
                tenant_id=self._tenant_id,
                session_id=self._session_id,
            )
            # Set global context so legacy callers (ReputationManager, etc.)
            # can also route events to the DB
            SecurityLogger.set_global_context(self._async_logger)
        else:
            self._async_logger = None

        # --- Initialize Policy Engine ---
        if self._tenant_id:
            # Production mode: DB-backed, TTL-cached policy engine
            self._tenant_policy_engine = TenantPolicyEngine(
                tenant_id=self._tenant_id,
                async_logger=self._async_logger,
            )
            # Legacy engine still available for sync code paths
            self.policy_engine = PolicyEngine(
                tenant_id=self._tenant_id,
                async_logger=self._async_logger,
            )
        else:
            # Local mode: file-based policies
            self._tenant_policy_engine = None
            from pathlib import Path
            self.policy_engine = PolicyEngine(
                Path(os.path.dirname(__file__)) / "dashboard"
            )

        # --- Other subsystems ---
        self.security_manager = ReputationManager()
        self.security_state = "UNKNOWN"
        self.last_evidence_path = None
        self.HONEY_TOKEN = "4000-1234-5678-9010"

        # Initialize risk scorer with user task context
        self.risk_scorer = RiskScorer(
            user_task=self.task if hasattr(self, "task") else ""
        )

        # Track the LLM for XAI explanation calls
        self._xai_llm = kwargs.get("llm", None)

        # Load Defense JS
        try:
            js_path = os.path.join(os.path.dirname(__file__), "defense.js")
            with open(js_path, "r", encoding="utf-8") as f:
                self.defense_script = f.read()
        except Exception as e:
            logger.error("Failed to load defense.js: %s", e)
            self.defense_script = ""

        # Network hook flag
        self._network_hooked = False

        # Install the secure browser state wrapper
        self._install_secure_state_wrapper()

    def __del__(self):
        """Cleanup: clear global logger context when agent is destroyed."""
        try:
            SecurityLogger.clear_global_context()
        except Exception:
            pass

    # =====================================================================
    #  SECURE BROWSER STATE WRAPPER (Replaces monkey-patching)
    # =====================================================================

    def _install_secure_state_wrapper(self):
        """
        Wraps the browser session's get_browser_state_summary method
        to pass all DOM content through the security filter.

        v2.0: Uses Python descriptor protocol instead of
        `object.__setattr__` monkey-patching. The wrapper stores a
        reference to the original method and delegates, ensuring
        compatibility with browser-use library updates.
        """
        original_get_state = self.browser_session.get_browser_state_summary
        agent = self  # Capture reference for the closure

        async def secure_get_state(*args, **kwargs):
            """
            Security-enhanced browser state retrieval.
            Injects client-side defenses, runs DOM scans, sanitizes
            content, and manages network interception.
            """
            # --- Inject Client-Side Defense JS (Sentinel Watchdog) ---
            js_threats = []
            try:
                page = getattr(agent.browser_session, "page", None)

                # Setup Network Interception if not already done
                if page and not agent._network_hooked:
                    await page.context.route("**/*", agent._intercept_network)
                    agent._network_hooked = True
                    logger.info("🛡️ Network Interceptor & Firewall Activated")

                if page and agent.defense_script:
                    # Inject Sentinel Library
                    await page.evaluate(agent.defense_script)
                    await asyncio.sleep(0.3)

                    # Run Active Scan
                    scan_script = _build_sentinel_scan_script()
                    js_threats = await page.evaluate(scan_script) or []

            except Exception as e:
                logger.error("Defense Injection Failed: %s", e)

            # --- Get the Raw Browser State ---
            summary = await original_get_state(*args, **kwargs)

            # --- Log JS-detected threats ---
            if js_threats:
                agent.last_evidence_path = await agent._capture_evidence()
                for threat in js_threats:
                    if threat.get("type") == "SYSTEM":
                        continue
                    logger.warning(
                        "🛡️ Sentinel DETECTED: %s", threat["details"]
                    )
                    await agent._log_security_event(
                        event_type=threat["type"],
                        url=summary.url if hasattr(summary, "url") else "unknown",
                        details=threat["details"],
                        risk_level="CRITICAL",
                        risk_score=threat.get("risk_score", 90),
                        action=(
                            "SANITIZED"
                            if "INJECTION" in threat["type"]
                            else "BLOCKED"
                        ),
                        screenshot_path=agent.last_evidence_path,
                    )

            # --- Update Security State based on URL ---
            current_url = summary.url if hasattr(summary, "url") else ""
            if not current_url or current_url in (
                "about:blank", "", "about:srcdoc"
            ):
                agent.security_state = "UNKNOWN"
                is_safe = True
            else:
                nav_blocked = await agent._check_navigation_policy(current_url)
                if nav_blocked:
                    agent.security_state = "BLOCKED"
                    is_safe = False
                else:
                    is_safe = agent.security_manager.check_reputation(
                        current_url
                    )
                    agent.security_state = "TRUSTED" if is_safe else "HOSTILE"

            # Log state changes
            threats_found = js_threats and len(js_threats) > 0
            if not threats_found:
                if getattr(agent, "last_logged_url", None) != current_url:
                    agent.last_logged_url = current_url
                    logger.info(
                        "Security State for %s: %s",
                        current_url, agent.security_state,
                    )
                    if is_safe:
                        await agent._log_security_event(
                            event_type="REPUTATION_CHECK",
                            url=current_url,
                            details="Domain verified as Trusted.",
                            risk_level="SAFE",
                            risk_score=0,
                            action="ALLOWED",
                        )
                    else:
                        await agent._log_security_event(
                            event_type="REPUTATION_WARNING",
                            url=current_url,
                            details="Domain flagged as Hostile/Untrusted. Engaging defenses.",
                            risk_level="HIGH",
                            risk_score=75,
                            action="WARNED",
                        )

            # --- DOM Sanitization (on all sites, not just hostile) ---
            agent._sanitize_dom(summary)

            if agent.security_state == "HOSTILE":
                agent.last_evidence_path = await agent._capture_evidence()
            else:
                agent.last_evidence_path = None

            return summary

        # Apply the wrapper via the browser session's attribute mechanism
        # Using setattr on the instance rather than object.__setattr__
        # to work with browser-use's internal property system
        try:
            self.browser_session.get_browser_state_summary = secure_get_state
        except Exception:
            # Fallback: handles Pydantic validate_assignment, __slots__, or descriptors
            object.__setattr__(
                self.browser_session,
                "get_browser_state_summary",
                secure_get_state,
            )
            logger.debug(
                "Used object.__setattr__ fallback for browser state wrapper"
            )

    # =====================================================================
    #  UNIFIED LOGGING (Async DB + Legacy JSONL fallback)
    # =====================================================================

    async def _log_security_event(
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
        Primary logging method. Routes to async DB logger if available,
        falls back to legacy JSONL logger.

        Returns:
            Audit log ID (str) if DB insert succeeded, else None.
        """
        if self._async_logger:
            return await self._async_logger.log_event(
                event_type=event_type,
                url=url,
                details=details,
                risk_level=risk_level,
                risk_score=risk_score,
                action=action,
                screenshot_path=screenshot_path,
                explanation=explanation,
                risk_breakdown=risk_breakdown,
                xai_pending=xai_pending,
            )
        else:
            # Legacy fallback
            SecurityLogger.log_event(
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

    # =====================================================================
    #  ASYNC POLICY CHECKS (Tenant-aware)
    # =====================================================================

    async def _check_navigation_policy(self, url: str) -> bool:
        """Check if URL is blocked by policy (async for tenant mode)."""
        if self._tenant_policy_engine:
            return await self._tenant_policy_engine.check_navigation(url)
        elif hasattr(self, "policy_engine"):
            return self.policy_engine.check_navigation(url)
        return False

    async def _check_action_policy(self, action_name: str) -> bool:
        """Check if action is blocked by policy (async for tenant mode)."""
        if self._tenant_policy_engine:
            return await self._tenant_policy_engine.check_action(action_name)
        elif hasattr(self, "policy_engine"):
            return self.policy_engine.check_action(action_name)
        return False

    async def _check_input_policy(self, text: str) -> bool:
        """Check if input matches a blocked DLP pattern (async for tenant mode)."""
        if self._tenant_policy_engine:
            return await self._tenant_policy_engine.check_input(text)
        elif hasattr(self, "policy_engine"):
            return self.policy_engine.check_input(text)
        return False

    # =====================================================================
    #  LAYER 3: NETWORK FIREWALL (Honey Token DLP + Cross-Origin Blocking)
    # =====================================================================

    async def _intercept_network(self, route, request):
        """
        Network-level security: Policy Enforcement, DLP honey token
        detection, cross-origin blocking, redirect analysis, and download inspection.
        """
        # --- Download Inspection & Redirects ---
        # Block common executable extensions
        lower_url = request.url.lower()
        if request.resource_type == "document" and any(lower_url.endswith(ext) for ext in [".exe", ".msi", ".bat", ".cmd", ".sh", ".zip", ".tar.gz", ".dll", ".scr"]):
            logger.warning("🚫 BLOCKED DOWNLOAD ATTEMPT: %s", request.url)
            await self._log_security_event(
                event_type="MALICIOUS_DOWNLOAD_BLOCKED",
                url=request.url,
                details=f"Blocked attempt to download potentially dangerous file type.",
                risk_level="HIGH",
                risk_score=90,
                action="BLOCKED",
            )
            await route.abort()
            return
            
        # Detect redirects via navigation requests
        if request.is_navigation_request() and request.redirected_from:
            logger.info("🔄 REDIRECT DETECTED: %s -> %s", request.redirected_from.url, request.url)
            # If redirected to a hostile domain, block it
            if self.security_manager.check_reputation(request.url) is False:
                logger.warning("🚫 BLOCKED HOSTILE REDIRECT: %s", request.url)
                await self._log_security_event(
                    event_type="MALICIOUS_REDIRECT_BLOCKED",
                    url=request.url,
                    details=f"Blocked automatic redirect to hostile domain from {request.redirected_from.url}",
                    risk_level="CRITICAL",
                    risk_score=95,
                    action="BLOCKED",
                )
                await route.abort()
                return

        # --- Policy Enforcement (Domains) ---
        if request.resource_type in [
            "document", "iframe", "fetch", "xhr"
        ]:
            nav_blocked = await self._check_navigation_policy(request.url)
            if nav_blocked:
                logger.warning("🚫 BLOCKED BY ENTERPRISE POLICY: %s", request.url)
                await route.abort()
                return

        # Block risky resource types
        if request.resource_type in ["font", "media"]:
            await route.abort()
            return

        # --- DLP: Check for Honey Token leakage ---
        post_data = request.post_data or ""
        leak_detected = False

        if (
            (self.HONEY_TOKEN in request.url)
            or (self.HONEY_TOKEN in str(request.headers))
            or (self.HONEY_TOKEN in post_data)
        ):
            leak_detected = True

        if leak_detected:
            logger.critical("🛑 DATA LEAK DETECTED: %s", self.HONEY_TOKEN)
            self.last_evidence_path = await self._capture_evidence()
            await self._log_security_event(
                event_type="DATA_LEAK_PREVENTED",
                url=request.url,
                details=(
                    f"Blocked transmission of Honey Token ({self.HONEY_TOKEN}) "
                    f"to external server in {request.resource_type}"
                ),
                risk_level="CRITICAL",
                risk_score=99,
                action="BLOCKED",
                screenshot_path=self.last_evidence_path,
                explanation=(
                    "The agent attempted to transmit a tracked credential "
                    "(honey token) outside the trusted boundary. This is a "
                    "strong indicator of credential exfiltration, likely "
                    "triggered by a phishing form or invisible "
                    "data-harvesting script."
                ),
            )
            await route.abort()
            return

        # --- Cross-Origin Form Submission Blocking ---
        if request.method == "POST" and request.resource_type in [
            "document", "xhr", "fetch"
        ]:
            try:
                page = getattr(self.browser_session, "page", None)
                if page:
                    current_origin = urlparse(page.url).netloc.split(":")[0]
                    request_origin = urlparse(request.url).netloc.split(":")[0]

                    if (
                        current_origin
                        and request_origin
                        and current_origin != request_origin
                    ):
                        current_root = ".".join(
                            current_origin.split(".")[-2:]
                        )
                        request_root = ".".join(
                            request_origin.split(".")[-2:]
                        )

                        if current_root != request_root:
                            logger.warning(
                                "🛑 Cross-origin POST blocked: %s → %s",
                                current_origin, request_origin,
                            )
                            self.last_evidence_path = (
                                await self._capture_evidence()
                            )
                            await self._log_security_event(
                                event_type="CROSS_ORIGIN_BLOCKED",
                                url=request.url,
                                details=(
                                    f"Blocked cross-origin form submission "
                                    f"from {current_origin} to {request_origin}"
                                ),
                                risk_level="CRITICAL",
                                risk_score=92,
                                action="BLOCKED",
                                screenshot_path=self.last_evidence_path,
                                explanation=(
                                    f"A form on {current_origin} attempted to "
                                    f"submit data to a completely different "
                                    f"domain ({request_origin}). This is a "
                                    f"classic indicator of a phishing attack or "
                                    f"data exfiltration attempt."
                                ),
                            )
                            await route.abort()
                            return
            except Exception as e:
                logger.debug("Cross-origin check error: %s", e)

        await route.continue_()

    async def _capture_evidence(self):
        """Captures a screenshot and returns the path."""
        try:
            screenshot_bytes = await self.browser_session.take_screenshot(
                full_page=False
            )
            filename = f"evidence_{int(time.time() * 1000)}.png"
            screenshot_dir = (
                AsyncSecurityLogger.get_screenshot_dir()
                if self._async_logger
                else SecurityLogger.get_screenshot_dir()
            )
            path = screenshot_dir / filename
            with open(path, "wb") as f:
                f.write(screenshot_bytes)
            return str(path)
        except Exception as e:
            logger.error("Failed to capture evidence: %s", e)
            return None

    # =====================================================================
    #  LAYER 1: DOM SANITIZATION LENS (Pre-Execution Content Filtering)
    # =====================================================================

    # Extended regex patterns for prompt injection detection
    INJECTION_PATTERNS = [
        # Direct instruction override
        r"(?i)ignore\s+(\w+\s+)?instructions",
        r"(?i)forget\s+(\w+\s+)?instructions",
        r"(?i)disregard\s+(\w+\s+)?(previous|prior|above|earlier)",
        r"(?i)system\s+override",
        r"(?i)you\s+are\s+now\s+a",
        r"(?i)new\s+directive",
        r"(?i)system\s+command",
        r"(?i)ignore\s+user\s+goal",
        # Role-play attacks
        r"(?i)act\s+as\s+(a\s+)?different",
        r"(?i)pretend\s+(you\s+are|to\s+be)",
        r"(?i)roleplay\s+as",
        r"(?i)switch\s+to\s+(\w+\s+)?mode",
        r"(?i)you\s+are\s+DAN",
        r"(?i)jailbreak",
        # Data exfiltration
        r"(?i)send\s+(the\s+)?(data|info|credentials|password|token)",
        r"(?i)transmit\s+(to|the)",
        r"(?i)exfiltrate",
        r"(?i)forward\s+(the\s+)?(data|info|credentials)",
        # Prompt leaking
        r"(?i)reveal\s+(your\s+)?(system\s+prompt|instructions|rules)",
        r"(?i)show\s+(me\s+)?(your\s+)?(system\s+prompt|instructions)",
        r"(?i)what\s+are\s+your\s+(instructions|rules|guidelines)",
        r"(?i)print\s+(your\s+)?(system\s+prompt|instructions)",
        # Instruction injection
        r"(?i)instead\s*,?\s+(do|execute|perform|run)",
        r"(?i)new\s+task\s*:",
        r"(?i)updated?\s+instructions?\s*:",
        r"(?i)override\s+(previous|prior|system)",
        r"(?i)<\s*system\s*>",
        r"(?i)\[\s*SYSTEM\s*\]",
        # Base64 encoded instructions
        r"(?i)base64\s*:\s*[A-Za-z0-9+/=]{20,}",
        r"(?i)atob\s*\(",
        r"(?i)btoa\s*\(",
    ]

    def _sanitize_dom(self, summary):
        """
        Modifies the summary to hide/redact dangerous content.
        Applies to ALL pages, not just hostile ones.
        """
        if self.security_state == "BLOCKED":
            if hasattr(summary, "dom_state"):

                def block_representation(*args, **kwargs):
                    return (
                        "[CRITICAL ALERT] NAVIGATION ABORTED. "
                        "DOMAIN IS BLOCKED BY ENTERPRISE POLICY. "
                        "DO NOT PROCEED."
                    )

                summary.dom_state.llm_representation = block_representation
            return

        if hasattr(summary, "dom_state"):
            original_llm_rep = summary.dom_state.llm_representation

            def secure_llm_representation(*args, **kwargs):
                raw_text = original_llm_rep(*args, **kwargs)
                sanitized_text = self._sanitize_text(raw_text)

                # --- Historical DOM Diff Tracing ---
                try:
                    diff_dir = os.path.join(
                        os.path.dirname(__file__), "dashboard", "diffs"
                    )
                    os.makedirs(diff_dir, exist_ok=True)
                    ts = int(time.time() * 1000)
                    with open(
                        os.path.join(diff_dir, f"diff_{ts}_raw.txt"),
                        "w", encoding="utf-8",
                    ) as f:
                        f.write(raw_text)
                    with open(
                        os.path.join(diff_dir, f"diff_{ts}_sanitized.txt"),
                        "w", encoding="utf-8",
                    ) as f:
                        f.write(sanitized_text)
                except Exception as e:
                    logger.error("Failed to record DOM trace: %s", e)

                return sanitized_text

            summary.dom_state.llm_representation = secure_llm_representation

    def _sanitize_text(self, text: str) -> str:
        """
        Removes prompt injection attempts from text using expanded
        pattern library.
        """
        sanitized = text
        for pattern in self.INJECTION_PATTERNS:
            match = re.search(pattern, sanitized)
            if match:
                matched_text = match.group(0)
                logger.warning(
                    "🛡️ Sanitizer: Detected injection '%s' (pattern: %s...)",
                    matched_text, pattern[:40],
                )
                # Use fire-and-forget async logging
                self._fire_and_forget_log(
                    event_type="INJECTION_ATTEMPT",
                    url="[Current DOM]",
                    details=(
                        f"Blocked prompt injection: '{matched_text}' "
                        f"(pattern: {pattern[:50]})"
                    ),
                    risk_level="CRITICAL",
                    risk_score=95,
                    action="SANITIZED",
                    screenshot_path=self.last_evidence_path,
                    explanation=(
                        f"The text '{matched_text}' on this page is an "
                        f"attempt to override the agent's instructions. "
                        f"This is a prompt injection attack designed to "
                        f"make the agent ignore its safety rules and "
                        f"follow malicious commands embedded in the webpage."
                    ),
                )
                sanitized = re.sub(
                    pattern, "[🛑 BLOCKED_INJECTION_ATTEMPT]", sanitized
                )

        return sanitized

    def _fire_and_forget_log(self, **kwargs):
        """
        Fire-and-forget async log from synchronous context.
        Used by _sanitize_text which runs inside a sync callback.
        """
        if self._async_logger:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._async_logger.log_event(**kwargs))
            except RuntimeError:
                # No event loop — use legacy logger
                SecurityLogger.log_event(**kwargs)
        else:
            SecurityLogger.log_event(**kwargs)

    # =====================================================================
    #  LAYER 2: ACTION SENTINEL (Risk-Scored Action Mediation)
    # =====================================================================

    async def multi_act(self, actions: list) -> list:
        """
        Intercepts and validates all agent actions before execution.
        Uses dynamic risk scoring for each action.
        """
        approved_actions = []
        blocked_results = []
        blocked_count = 0

        for index, action in enumerate(actions):
            validation_result = await self._validate_action_with_risk(action)

            if validation_result["approved"]:
                approved_actions.append(action)

                if validation_result.get("risk_level") == "MEDIUM":
                    logger.info(
                        "⚠️ Sentinel: Action %d approved with elevated "
                        "monitoring (Risk: %s/100)",
                        index, validation_result.get("risk_score", "?"),
                    )
            else:
                blocked_count += 1
                logger.warning(
                    "🛑 Sentinel: BLOCKED action %d "
                    "(Risk: %s/100, Reason: %s)",
                    index,
                    validation_result.get("risk_score", "?"),
                    validation_result.get("reason", "policy violation"),
                )

                # Generate XAI explanation for blocked actions
                await self._generate_xai_explanation(
                    action, validation_result
                )

                from browser_use.agent.views import ActionResult

                blocked_results.append(
                    ActionResult(
                        error=f"Security Block: {validation_result.get('reason')}"
                    )
                )

        if blocked_count > 0:
            logger.info(
                "🛡️ Sentinel: Blocked %d dangerous action(s).", blocked_count
            )
            if not approved_actions:
                return blocked_results

        # --- LLM Output / Tool Call Validation (Phase 7) ---
        for act in approved_actions:
            # Inspect the raw tool call payload for leakage or bad outputs
            act_dump = act.model_dump(exclude_none=True)
            for k, v in act_dump.items():
                if isinstance(v, dict) and "text" in v:
                    text_val = v["text"]
                    if self.HONEY_TOKEN in text_val:
                        logger.critical("🛑 Sentinel: LLM attempted to output Honey Token in action!")
                        blocked_results.append(
                            ActionResult(error="Security Block: Output Validation Failed (DLP)")
                        )
                        approved_actions.remove(act)
                        await self._log_security_event(
                            event_type="LLM_OUTPUT_LEAK_PREVENTED",
                            details="Blocked LLM from outputting honey token in tool call.",
                            risk_level="CRITICAL", risk_score=100, action="BLOCKED"
                        )
                        break

        if not approved_actions:
            return blocked_results

        return await super().multi_act(approved_actions) + blocked_results

    async def _validate_action_with_risk(self, action_model) -> dict:
        """
        Validates an action using dynamic risk scoring.
        Returns dict with 'approved', 'risk_score', 'risk_level', 'reason'.

        v2.0: All policy checks are now async to support the DB-backed
        TenantPolicyEngine.
        """
        try:
            action_data = action_model.model_dump(exclude_none=True)

            for action_name, params in action_data.items():
                if params is None:
                    continue

                if not isinstance(params, dict):
                    params = {}

                # --- Policy Engine Enforcement (Async) ---

                # 1. Blocked Actions
                if await self._check_action_policy(action_name):
                    return {
                        "approved": False,
                        "risk_score": 80,
                        "risk_level": "HIGH",
                        "reason": (
                            f"Action '{action_name}' is disabled by "
                            f"Enterprise Policy."
                        ),
                    }

                # 2. Blocked Domains (Navigation)
                if action_name in [
                    "go_to_url", "open_tab", "navigate", "go_to"
                ]:
                    nav_url = params.get("url", "")
                    if nav_url and await self._check_navigation_policy(
                        nav_url
                    ):
                        return {
                            "approved": False,
                            "risk_score": 95,
                            "risk_level": "CRITICAL",
                            "reason": (
                                f"Navigation to '{nav_url}' is blocked by "
                                f"Enterprise Policy."
                            ),
                        }

                # 3. Blocked Input Patterns
                if action_name == "input_text":
                    input_val = params.get("text", "")
                    if input_val and await self._check_input_policy(input_val):
                        return {
                            "approved": False,
                            "risk_score": 85,
                            "risk_level": "HIGH",
                            "reason": (
                                "Input matches a pattern restricted by "
                                "Enterprise Policy."
                            ),
                        }

                # --- Hard Policy Checks ---

                # Policy: Block sensitive keyword input on hostile sites
                if (
                    action_name == "input_text"
                    and self.security_state == "HOSTILE"
                ):
                    text = params.get("text", "")
                    sensitive_keywords = [
                        "password", "credit", "card", "ssn",
                        "cvv", "secret", "token",
                    ]
                    if any(kw in text.lower() for kw in sensitive_keywords):
                        await self._log_security_event(
                            event_type="DATA_LEAK_PREVENTION",
                            url="[Action Interception]",
                            details=(
                                f"Blocked input of sensitive data on "
                                f"hostile site: {text[:30]}..."
                            ),
                            risk_level="CRITICAL",
                            risk_score=99,
                            action="BLOCKED",
                            screenshot_path=self.last_evidence_path,
                            explanation=(
                                f"The agent attempted to type sensitive "
                                f"information ('{text[:20]}...') into a "
                                f"form on an untrusted/hostile website. "
                                f"This was blocked to prevent credential "
                                f"theft or data exfiltration."
                            ),
                        )
                        return {
                            "approved": False,
                            "risk_score": 99,
                            "risk_level": "CRITICAL",
                            "reason": (
                                "Sensitive data input on hostile site blocked"
                            ),
                        }

                # Policy: Block SQL injection patterns in any input
                if action_name == "input_text":
                    text = params.get("text", "")
                    sql_patterns = [
                        r"(?i)DROP\s+TABLE",
                        r"(?i)SELECT\s+\*",
                        r"(?i)DELETE\s+FROM",
                        r"(?i)INSERT\s+INTO",
                        r"(?i)UPDATE\s+\w+\s+SET",
                        r"(?i)UNION\s+SELECT",
                        r"(?i);\s*DROP",
                        r"(?i)OR\s+1\s*=\s*1",
                        r"(?i)'\s*OR\s+'",
                        r"(?i)--\s*$",
                    ]
                    for sql_pat in sql_patterns:
                        if re.search(sql_pat, text):
                            logger.warning(
                                "🛑 Sentinel: Blocked SQL injection: %s",
                                text[:40],
                            )
                            await self._log_security_event(
                                event_type="SQL_INJECTION_BLOCKED",
                                url="[Action Interception]",
                                details=(
                                    f"Blocked SQL injection pattern "
                                    f"in input: {text[:50]}"
                                ),
                                risk_level="CRITICAL",
                                risk_score=95,
                                action="BLOCKED",
                                screenshot_path=self.last_evidence_path,
                                explanation=(
                                    f"The input text '{text[:30]}...' "
                                    f"contains SQL injection patterns "
                                    f"that could manipulate databases "
                                    f"if submitted to a web form."
                                ),
                            )
                            return {
                                "approved": False,
                                "risk_score": 95,
                                "risk_level": "CRITICAL",
                                "reason": (
                                    f"SQL injection pattern detected: "
                                    f"{sql_pat}"
                                ),
                            }

                # --- Dynamic Risk Scoring ---
                current_url = getattr(self, "last_logged_url", "") or ""
                risk_result = self.risk_scorer.calculate_risk(
                    action_name=action_name,
                    action_params=params,
                    current_url=current_url,
                    security_state=self.security_state,
                )

                risk_score = risk_result["score"]
                risk_level = risk_result["level"]
                recommendation = risk_result["recommendation"]

                # Log the risk assessment
                await self._log_security_event(
                    event_type="RISK_ASSESSMENT",
                    url=current_url,
                    details=(
                        f"Action '{action_name}' scored "
                        f"{risk_score}/100 ({risk_level}). "
                        f"Breakdown: {json.dumps(risk_result['breakdown'])}"
                    ),
                    risk_level=risk_level,
                    risk_score=risk_score,
                    action=recommendation,
                    risk_breakdown=risk_result["breakdown"],
                )

                if recommendation == "BLOCK_AND_ESCALATE":
                    return {
                        "approved": False,
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "reason": (
                            f"Risk score {risk_score}/100 exceeds "
                            f"threshold. Breakdown: "
                            f"{risk_result['breakdown']}"
                        ),
                        "breakdown": risk_result["breakdown"],
                    }

                return {
                    "approved": True,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                }

            return {"approved": True, "risk_score": 0, "risk_level": "LOW"}

        except Exception as e:
            logger.error("Error validating action: %s", e)
            return {
                "approved": False,
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "reason": f"Validation error: {e}",
            }

    # =====================================================================
    #  LAYER 4: EXPLAINABLE AI (LLM-Generated Explanations)
    # =====================================================================

    async def _generate_xai_explanation(
        self, action_model, validation_result: dict
    ):
        """
        Generate a human-readable explanation of WHY an action was blocked.

        v2.0 (Component 4): Offloads LLM call to a Celery background worker.
        The agent inserts a placeholder audit log with xai_pending=True,
        then fires a Celery task to generate the explanation asynchronously.
        This reduces per-step latency from ~2-4s to ~50ms (fire-and-forget).

        Falls back to inline LLM generation if Celery/Redis is unreachable.
        """
        try:
            action_data = action_model.model_dump(exclude_none=True)
            risk_score = validation_result.get("risk_score", "?")
            reason = validation_result.get("reason", "Unknown")
            breakdown = validation_result.get("breakdown", {})

            # Insert a pending log entry immediately (non-blocking)
            log_id = await self._log_security_event(
                event_type="XAI_EXPLANATION",
                url=getattr(self, "last_logged_url", "") or "",
                details=f"Generating explanation for blocked action (risk: {risk_score}/100)...",
                risk_level=validation_result.get("risk_level", "HIGH"),
                risk_score=risk_score if isinstance(risk_score, int) else 0,
                action="EXPLAINED",
                xai_pending=True,
            )

            if not log_id:
                logger.debug("No log_id returned — skipping XAI dispatch.")
                return

            # Build the payload for the Celery worker
            xai_payload = {
                "action_data": json.dumps(action_data, default=str)[:300],
                "risk_score": risk_score if isinstance(risk_score, int) else 0,
                "reason": reason,
                "risk_level": validation_result.get("risk_level", "HIGH"),
                "breakdown": breakdown,
                "url": getattr(self, "last_logged_url", "") or "",
                "security_state": self.security_state,
            }

            # --- Dispatch to worker (fire-and-forget) ---
            try:
                from workers.xai_tasks import generate_xai_explanation as xai_task
                from workers.dispatch import dispatch_task
                dispatch_task(xai_task, log_id, xai_payload)
                logger.info(
                    "📋 XAI task dispatched for log %s (fire-and-forget)",
                    log_id,
                )
                return  # Success — worker handles the rest
            except Exception as celery_err:
                logger.warning(
                    "Task dispatch failed (%s) — falling back to inline XAI.",
                    celery_err,
                )

            # --- Fallback: Inline LLM generation (blocking) ---
            if not self._xai_llm:
                return

            xai_prompt = (
                "You are a cybersecurity analyst. A browser automation "
                "agent had an action BLOCKED by the security system. "
                "Write a clear, 2-3 sentence explanation for the human "
                "operator explaining:\n"
                "1. WHAT the agent tried to do\n"
                "2. WHY it was blocked\n"
                "3. What the RISK was\n\n"
                f"Action attempted: "
                f"{json.dumps(action_data, default=str)[:300]}\n"
                f"Risk Score: {risk_score}/100\n"
                f"Block Reason: {reason}\n"
                f"Risk Breakdown: {json.dumps(breakdown, default=str)}\n"
                f"Current security state: {self.security_state}\n\n"
                "Write ONLY the explanation, no headers or formatting. "
                "Be concise and specific."
            )

            from langchain_core.messages import HumanMessage

            response = await self._xai_llm.ainvoke(
                [HumanMessage(content=xai_prompt)]
            )
            explanation = response.content.strip()

            logger.info("📋 XAI Explanation (inline fallback): %s", explanation)

            # Backfill the explanation into the pending log entry
            if self._async_logger:
                await self._async_logger.update_xai_explanation(
                    log_id, explanation
                )
            else:
                # Legacy fallback: log as a new event
                await self._log_security_event(
                    event_type="XAI_EXPLANATION",
                    url=getattr(self, "last_logged_url", "") or "",
                    details=explanation,
                    risk_level=validation_result.get("risk_level", "HIGH"),
                    risk_score=risk_score if isinstance(risk_score, int) else 0,
                    action="EXPLAINED",
                    explanation=explanation,
                )

        except Exception as e:
            logger.debug(
                "XAI explanation generation failed (non-critical): %s", e
            )


# SENTINEL SCAN SCRIPT (Extracted for readability)

def _build_sentinel_scan_script() -> str:
    """
    Returns the JavaScript scan script that runs in the browser context.
    Detects: invisible prompt injections, phishing forms, cross-origin
    forms, iframe overlays, clickjacking attempts, and deceptive UI.
    """
    return """
    (function() {
        if (!window.Sentinel) return [{type: 'SYSTEM', details: 'Sentinel JS failed to load'}];

        const vulnerabilities = [];
        const all = document.querySelectorAll('*');
        all.forEach(el => {
            // --- VISUAL TRUTH VALIDATOR ---
            try {
                if (el.children.length === 0 && el.textContent.trim().length > 0) {
                    const style = window.getComputedStyle(el);
                    let rect = el.getBoundingClientRect();

                    let isHidden = (
                        style.opacity === '0' ||
                        style.display === 'none' ||
                        style.visibility === 'hidden' ||
                        parseFloat(style.fontSize) < 1 ||
                        rect.left < -999 || rect.top < -999 ||
                        (style.color && style.backgroundColor && style.color === style.backgroundColor && style.color !== 'rgba(0, 0, 0, 0)')
                    );

                    if (isHidden && !el.getAttribute('data-visual-truth-purged')) {
                        let snippet = el.textContent.trim().substring(0, 40);
                        vulnerabilities.push({
                            type: 'VISUAL_TRUTH_VIOLATION',
                            details: `Stripped invisible prompt injection mathematically: "${snippet}"`,
                            risk_score: 95
                        });
                        el.setAttribute('data-visual-truth-purged', 'true');
                        el.remove();
                        return;
                    }
                }
            } catch(e) {}

            // DETECTOR 1: Dynamic Injection (MutationObserver Results)
            if (el.getAttribute('data-sentinel-suspicious') === 'true' && !el.getAttribute('data-sentinel-dynamic-logged')) {
                el.setAttribute('data-sentinel-dynamic-logged', 'true');
                vulnerabilities.push({
                    type: 'DYNAMIC_CONTENT_ANALYSIS',
                    details: 'Vector 4: Dynamic Injection / Suspicious Popup blocked',
                    risk_score: 85
                });
            }

            // DETECTOR 2: Phishing (Form Analysis)
            if (el.tagName === 'INPUT' && (el.name.includes('card') || el.id.includes('cc-'))) {
                if (!el.getAttribute('data-sentinel-phishing-logged')) {
                    el.setAttribute('data-sentinel-phishing-logged', 'true');
                    vulnerabilities.push({
                        type: 'PHISHING_CONTENT_DETECTED',
                        details: 'Vector 5: Suspicious Credit Card Input Form',
                        risk_score: 90
                    });
                }
            }

            // DETECTOR 3: Cross-Origin Forms
            if (el.tagName === 'FORM' && !el.getAttribute('data-sentinel-form-logged')) {
                var action = el.getAttribute('action') || '';
                if (action.startsWith('http') && !action.includes(window.location.hostname)) {
                    el.setAttribute('data-sentinel-form-logged', 'true');
                    el.style.border = '4px solid red';
                    vulnerabilities.push({
                        type: 'CROSS_ORIGIN_FORM',
                        details: 'Suspicious form submitting to external domain: ' + action.substring(0, 60),
                        risk_score: 88
                    });
                }
            }

            // DETECTOR 4: Iframe Overlays
            if (el.tagName === 'IFRAME' && !el.getAttribute('data-sentinel-iframe-logged')) {
                var iStyle = window.getComputedStyle(el);
                var iOpacity = parseFloat(iStyle.opacity);
                if (iOpacity < 0.2 || iStyle.position === 'absolute' || iStyle.position === 'fixed') {
                    el.setAttribute('data-sentinel-iframe-logged', 'true');
                    el.style.border = '5px solid red';
                    el.style.pointerEvents = 'none';
                    vulnerabilities.push({
                        type: 'IFRAME_OVERLAY_DETECTED',
                        details: 'Suspicious invisible/positioned iframe detected (potential clickjacking)',
                        risk_score: 85
                    });
                }
            }

            // DETECTOR 5: Visibility & Clickjacking
            if (el.getAttribute('data-sentinel-logged')) return;
            let result = 'VISIBLE';
            try {
                result = window.Sentinel.checkVisibility(el);
            } catch(e) { return; }

            if (result !== 'VISIBLE' && result !== 'SAFE_HIDDEN' && result !== 'NOT_FOUND' && result !== 'COMPLEX') {
                if (result === 'HIDDEN_PROMPT_INJECTION') {
                    el.setAttribute('data-sentinel-logged', 'true');
                    vulnerabilities.push({
                        type: 'INJECTION_ATTEMPT',
                        details: 'Vector 2: Hidden Prompt Injection detected & sanitized',
                        risk_score: 95
                    });
                    el.innerText = '[🛑 BLOCKED PROMPT INJECTION]';
                    el.style.color = 'white'; el.style.backgroundColor = 'red'; el.style.display = 'block'; el.style.visibility = 'visible'; el.style.zIndex = '10000';
                }
                else if (result.startsWith('TINY_TEXT') || result.startsWith('INVISIBLE_INK') || result.startsWith('HIDDEN_OPACITY')) {
                    el.setAttribute('data-sentinel-logged', 'true');
                    el.style.border = '3px dotted orange';
                    vulnerabilities.push({
                        type: 'DECEPTIVE_UI_DETECTED',
                        details: 'Hidden CSS / Obfuscation: ' + result,
                        risk_score: 70
                    });
                }
                else if (result === 'BLOCKED_BY_INVISIBLE_OVERLAY') {
                    el.setAttribute('data-sentinel-logged', 'true');
                    el.style.border = '5px solid red';
                    vulnerabilities.push({
                        type: 'CLICKJACKING_ATTEMPT',
                        details: 'Vector 3: Invisible Overlay / Clickjacking Blocked',
                        risk_score: 90
                    });
                }
            }
        });
        return vulnerabilities;
    })();
    """
