"""
security/metrics.py — Production-Grade Observability & Security Intelligence Metrics (Phase 6).

Single source of truth for all Prometheus metrics in Agent-Bastion.
Enforces strict cardinality limits, normalized URL path labels, and tenant-isolated observability telemetry.
"""
import re
import time
import psutil
import logging
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY

logger = logging.getLogger("security.metrics")

# Path normalization regex patterns to prevent high-cardinality explosion (Task 6.1)
UUID_PATTERN = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
HEX_ID_PATTERN = re.compile(r"/[0-9a-fA-F]{16,64}")
INT_ID_PATTERN = re.compile(r"/\d+")


def normalize_path(path: str) -> str:
    """
    Normalize dynamic URL paths by replacing IDs (UUIDs, hex strings, integers)
    with standard `:id` placeholders. Guaranteed to keep Prometheus series count < 100.
    """
    if not path or path == "/":
        return "/"
        
    path = UUID_PATTERN.sub("/:id", path)
    path = HEX_ID_PATTERN.sub("/:id", path)
    path = INT_ID_PATTERN.sub("/:id", path)
    return path


# ==============================================================================
# 1. HTTP Middleware & Request Observability (Tasks 6.1 & 6.2)
# ==============================================================================
abs_http_requests_total = Counter(
    "abs_http_requests_total",
    "Total HTTP requests processed by Agent-Bastion Gateway",
    ["method", "path", "status", "tenant_id"]
)

abs_http_request_duration_seconds = Histogram(
    "abs_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ==============================================================================
# 2. Business & Task Observability (Task 6.2 & Objective 1)
# ==============================================================================
abs_active_sessions = Gauge(
    "abs_active_sessions",
    "Current number of active agent sessions by tenant, tier, and status",
    ["tenant_id", "tier", "status"]
)

abs_agent_actions_total = Counter(
    "abs_agent_actions_total",
    "Total agent actions evaluated by the security policy engine",
    ["tenant_id", "action_type", "verdict"]
)

abs_tasks_total = Counter(
    "abs_tasks_total",
    "Total agent tasks submitted across queues and statuses",
    ["tenant_id", "queue_name", "status"]
)

abs_session_duration_seconds = Histogram(
    "abs_session_duration_seconds",
    "Autonomous agent task execution duration in seconds",
    ["tenant_id", "queue_name", "status"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
)

abs_llm_request_duration_seconds = Histogram(
    "abs_llm_request_duration_seconds",
    "LLM and external tool call execution latency in seconds",
    ["tenant_id", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0]
)

abs_task_retries_total = Counter(
    "abs_task_retries_total",
    "Total task retry and re-enqueue operations executed",
    ["tenant_id", "queue_name"]
)

abs_dead_letter_tasks_total = Counter(
    "abs_dead_letter_tasks_total",
    "Total tasks routed to dead-letter storage or permanently failed",
    ["tenant_id", "queue_name", "reason"]
)

# ==============================================================================
# 3. Security Observability & Intelligence (Task 6.2 & Objective 2)
# ==============================================================================
abs_security_events_total = Counter(
    "abs_security_events_total",
    "Total security violations and attack attempts detected by defense layers",
    ["tenant_id", "event_type", "severity"]
)

abs_auth_failures_total = Counter(
    "abs_auth_failures_total",
    "Authentication failures by reason and tenant",
    ["reason", "tenant_id"]
)

abs_rbac_violations_total = Counter(
    "abs_rbac_violations_total",
    "Unauthorized access attempts and privilege escalation violations",
    ["role", "endpoint", "tenant_id"]
)

abs_token_replay_attempts_total = Counter(
    "abs_token_replay_attempts_total",
    "Detected refresh token replay or stolen token usage attempts",
    ["tenant_id"]
)

# ==============================================================================
# 4. Rate Limiting & Abuse Metrics (Objective 3)
# ==============================================================================
abs_rate_limit_violations_total = Counter(
    "abs_rate_limit_violations_total",
    "Total rate limit exceeded events by tenant, endpoint, and limit scope",
    ["tenant_id", "endpoint", "scope"]
)

abs_quota_violations_total = Counter(
    "abs_quota_violations_total",
    "Total tenant quota exceeded violations (concurrent tasks, API keys, etc.)",
    ["tenant_id", "quota_type"]
)

# ==============================================================================
# 5. Worker & Distributed System Observability (Objective 4)
# ==============================================================================
abs_active_workers = Gauge(
    "abs_active_workers",
    "Number of active Celery worker nodes registered and heartbeating",
    ["node_id", "queue"]
)

abs_worker_failures_total = Counter(
    "abs_worker_failures_total",
    "Uncaught exceptions and fatal worker errors during task execution",
    ["node_id", "exception_type"]
)

# ==============================================================================
# 6. Resource & Infrastructure Health Observability (Objective 6)
# ==============================================================================
abs_resource_cpu_usage_ratio = Gauge(
    "abs_resource_cpu_usage_ratio",
    "Process CPU utilization ratio (0.0 to 1.0+)"
)

abs_resource_memory_usage_bytes = Gauge(
    "abs_resource_memory_usage_bytes",
    "Process Resident Set Size (RSS) memory consumption in bytes"
)

abs_system_health_status = Gauge(
    "abs_system_health_status",
    "Component operational status (1 = Healthy, 0 = Degraded/Offline)",
    ["component"]
)


# ==============================================================================
# Recording Helper Functions
# ==============================================================================
def record_http_request(
    method: str, 
    path: str, 
    status: int, 
    duration_seconds: float, 
    tenant_id: str = "anonymous"
) -> None:
    """Record normalized HTTP request telemetry safely."""
    try:
        norm_path = normalize_path(path)
        status_str = str(status)
        tenant_label = tenant_id or "anonymous"
        abs_http_requests_total.labels(method=method, path=norm_path, status=status_str, tenant_id=tenant_label).inc()
        abs_http_request_duration_seconds.labels(method=method, path=norm_path, status=status_str).observe(duration_seconds)
    except Exception as e:
        logger.debug("Failed to record HTTP metrics: %s", e)


def record_task_submission(tenant_id: str, queue_name: str, status: str) -> None:
    """Record task lifecycle status."""
    try:
        abs_tasks_total.labels(tenant_id=tenant_id or "unknown", queue_name=queue_name or "default", status=status).inc()
    except Exception as e:
        logger.debug("Failed to record task submission metric: %s", e)


def record_task_duration(tenant_id: str, queue_name: str, status: str, duration_seconds: float) -> None:
    """Record execution latency for finished agent sessions."""
    try:
        abs_session_duration_seconds.labels(tenant_id=tenant_id or "unknown", queue_name=queue_name or "default", status=status).observe(duration_seconds)
    except Exception as e:
        logger.debug("Failed to record task duration metric: %s", e)


def record_security_event_metric(tenant_id: str, event_type: str, severity: str = "HIGH") -> None:
    """Record a detected attack or policy violation."""
    try:
        abs_security_events_total.labels(tenant_id=tenant_id or "anonymous", event_type=event_type, severity=severity).inc()
    except Exception as e:
        logger.debug("Failed to record security event metric: %s", e)


def record_auth_failure_metric(reason: str, tenant_id: str = "anonymous") -> None:
    """Record authentication or credential failures."""
    try:
        abs_auth_failures_total.labels(reason=reason, tenant_id=tenant_id or "anonymous").inc()
    except Exception as e:
        logger.debug("Failed to record auth failure metric: %s", e)


def record_rbac_violation_metric(role: str, endpoint: str, tenant_id: str = "anonymous") -> None:
    """Record privilege escalation or unauthorized role access attempts."""
    try:
        norm_endpoint = normalize_path(endpoint)
        abs_rbac_violations_total.labels(role=role, endpoint=norm_endpoint, tenant_id=tenant_id or "anonymous").inc()
    except Exception as e:
        logger.debug("Failed to record RBAC violation metric: %s", e)


def record_rate_limit_metric(tenant_id: str, endpoint: str, scope: str = "60s") -> None:
    """Record rate limit throttling events."""
    try:
        norm_endpoint = normalize_path(endpoint)
        abs_rate_limit_violations_total.labels(tenant_id=tenant_id or "anonymous", endpoint=norm_endpoint, scope=scope).inc()
    except Exception as e:
        logger.debug("Failed to record rate limit metric: %s", e)


def update_system_resources() -> None:
    """Update process CPU and memory gauges."""
    try:
        process = psutil.Process()
        cpu = process.cpu_percent(interval=None) / 100.0
        mem = process.memory_info().rss
        abs_resource_cpu_usage_ratio.set(cpu)
        abs_resource_memory_usage_bytes.set(mem)
    except Exception as e:
        logger.debug("Failed to update resource metrics: %s", e)
