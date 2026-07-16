"""
agent_bastion.client — Authoritative Python Client Library for Agent-Bastion v2.0.

Provides synchronous and asynchronous methods for submitting agent sessions, monitoring
execution lifecycles, managing tenants/API keys, and inspecting system health.
"""

import os
import json
from typing import Optional, Dict, Any, Union, List
import httpx

from agent_bastion.exceptions import (
    AgentBastionError,
    AuthenticationError,
    RateLimitError,
    TenantIsolationError,
    TaskExecutionError,
    ConnectionError,
)
from agent_bastion.models import (
    TaskSubmission,
    AgentSession,
    TaskMetrics,
    WorkerMetrics,
    HealthStatus,
    TenantConfig,
    APIKeyInfo,
)


class Client:
    """
    Production-grade Python Client for Agent-Bastion.

    Usage:
        ```python
        from agent_bastion import Client

        client = Client(api_key="abs_ak_prod_123456789")
        session = client.create_agent_session(
            task_prompt="Extract top 5 news articles and summarize titles",
            target_url="https://news.ycombinator.com"
        )
        status = client.get_status(session["session_id"])
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the Agent-Bastion SDK Client.

        Args:
            api_key: API Key for tenant authentication. Defaults to `AGENT_BASTION_API_KEY` env var.
            base_url: Base HTTP URL of the Agent-Bastion gateway. Defaults to `AGENT_BASTION_BASE_URL` or `http://localhost:8000`.
            timeout: Default HTTP request timeout in seconds.
            headers: Optional dictionary of additional custom HTTP headers.
        """
        self.api_key = api_key or os.getenv("AGENT_BASTION_API_KEY") or os.getenv("ABS_API_KEY")
        raw_base_url = base_url or os.getenv("AGENT_BASTION_BASE_URL") or os.getenv("ABS_BASE_URL") or "http://localhost:8000"
        self.base_url = raw_base_url.rstrip("/")
        self.timeout = timeout

        self._default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AgentBastion-PythonSDK/2.0.0",
        }
        if self.api_key:
            self._default_headers["X-API-Key"] = self.api_key
            self._default_headers["Authorization"] = f"Bearer {self.api_key}"
        if headers:
            self._default_headers.update(headers)

        self._http_client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._default_headers,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Internal HTTP request dispatcher with structured exception mapping."""
        url = path if path.startswith("/") else f"/{path}"
        try:
            response = self._http_client.request(method=method, url=url, params=params, json=json_data)
        except httpx.ConnectError as exc:
            raise ConnectionError(f"Failed to connect to Agent-Bastion server at {self.base_url}: {str(exc)}")
        except httpx.TimeoutException as exc:
            raise ConnectionError(f"Request to {self.base_url}{url} timed out after {self.timeout}s: {str(exc)}")
        except Exception as exc:
            raise AgentBastionError(f"Unexpected error communicating with Agent-Bastion: {str(exc)}")

        if response.status_code == 401:
            raise AuthenticationError("Authentication failed: Invalid API key or expired credentials.", status_code=401)
        elif response.status_code == 403:
            raise TenantIsolationError("Access denied: Insufficient role permissions or tenant boundary violation.", status_code=403)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_int = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise RateLimitError(
                "API rate limit or tenant quota exceeded. Please slow down requests.",
                retry_after=retry_int,
            )
        elif response.status_code >= 400:
            try:
                err_body = response.json()
                msg = err_body.get("detail") or err_body.get("message") or f"HTTP Error {response.status_code}"
            except Exception:
                msg = f"HTTP Error {response.status_code}: {response.text[:200]}"
            raise AgentBastionError(msg, status_code=response.status_code)

        if response.status_code == 204 or not response.content:
            return {"status": "success"}

        try:
            return response.json()
        except Exception:
            return {"raw_output": response.text}

    # ── 1. Core Agent Lifecycle Methods (Task 1) ──────────────────────

    def create_agent_session(
        self,
        task_prompt: str,
        target_url: Optional[str] = None,
        queue_name: Optional[str] = None,
        priority: Optional[int] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Submit a new autonomous browser agent task for execution inside secure worker sandboxes.

        Args:
            task_prompt: Natural language instructions describing what the agent should do.
            target_url: Optional web address where the agent should start browsing.
            queue_name: Optional target worker queue (`agents`, `priority_agents`).
            priority: Optional execution priority (`1` highest to `10` lowest).
            max_retries: Number of automated retries upon browser automation failure.
            **kwargs: Extra parameters forwarded to the session creation payload.

        Returns:
            Dictionary containing `session_id`, `status`, `queue_name`, and `priority`.
        """
        payload = {
            "task_prompt": task_prompt,
            "target_url": target_url,
            "queue_name": queue_name,
            "priority": priority,
            "max_retries": max_retries,
        }
        payload.update(kwargs)
        # Remove keys that are explicitly None so backend defaults apply cleanly
        clean_payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", "/api/v1/agents", json_data=clean_payload)

    def get_status(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve live status, step progression, and execution output of an agent session.

        Args:
            session_id: Unique UUID of the target session.

        Returns:
            Dictionary with session status, current URL, step count, and result summary.
        """
        return self._request("GET", f"/api/v1/agents/{session_id}")

    def cancel(self, session_id: str) -> Dict[str, Any]:
        """
        Instantly cancel/revoke a queued or currently running agent session.

        Args:
            session_id: Unique UUID of the target session to cancel.

        Returns:
            Confirmation dictionary indicating successful cancellation.
        """
        return self._request("POST", f"/api/v1/agents/{session_id}/cancel")

    def retry(self, session_id: str) -> Dict[str, Any]:
        """
        Retry a previously failed agent session, moving it back into the active worker queue.

        Args:
            session_id: Unique UUID of the failed session.

        Returns:
            Updated session status dictionary.
        """
        return self._request("POST", f"/api/v1/agents/{session_id}/retry")

    def metrics(self) -> Dict[str, Any]:
        """
        Retrieve platform-wide or tenant-specific task execution and worker queue metrics.

        Returns:
            Dictionary containing `total_tasks`, `completed_tasks`, queue depths, and worker counts.
        """
        try:
            return self._request("GET", "/api/v1/observability/tasks")
        except AgentBastionError:
            # Fallback for direct worker queue stats inspection
            return self._request("GET", "/api/v1/agents/queues/stats")

    # ── 2. Health & Diagnostic Methods (CLI & Onboarding) ─────────────

    def check_health(self) -> Dict[str, Any]:
        """
        Inspect the status and latency of the API gateway, PostgreSQL database, and Celery workers.

        Returns:
            System health dictionary.
        """
        try:
            return self._request("GET", "/api/v1/observability/health")
        except AgentBastionError:
            return self._request("GET", "/health")

    # ── 3. Tenant & API Key Management Methods (Quickstart Workflow) ──

    def create_tenant(
        self,
        name: str,
        tier: str = "PRO",
        contact_email: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Register a new multi-tenant organization within Agent-Bastion.

        Args:
            name: Organization / tenant name.
            tier: Assigned service tier (`FREE`, `PRO`, `ENTERPRISE`).
            contact_email: Optional administrator email address.

        Returns:
            Created tenant configuration dictionary including initial `api_key`.
        """
        payload = {"name": name, "tier": tier.upper(), "contact_email": contact_email}
        payload.update(kwargs)
        clean_payload = {k: v for k, v in payload.items() if v is not None}
        return self._request("POST", "/api/v1/tenants", json_data=clean_payload)

    def generate_api_key(
        self,
        tenant_id: Optional[str] = None,
        name: str = "default-sdk-key",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate a new cryptographic API key for authentication and rate-limit quota tracking.

        Args:
            tenant_id: Target tenant ID (optional if creating for authenticated tenant).
            name: Descriptive label for the API key.

        Returns:
            Dictionary containing plaintext `api_key`, `key_prefix`, and quota boundaries.
        """
        payload = {"name": name}
        if tenant_id:
            payload["tenant_id"] = tenant_id
        payload.update(kwargs)
        return self._request("POST", "/api/v1/api-keys", json_data=payload)

    def close(self) -> None:
        """Close underlying HTTP connection pool cleanly."""
        if hasattr(self, "_http_client") and self._http_client:
            self._http_client.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Backward compatibility alias
AgentBastionClient = Client
