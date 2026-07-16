"""
agent_bastion.models — Structured data representations for Agent-Bastion SDK responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TaskSubmission(BaseModel):
    """Payload returned upon submitting a new agent session/task."""
    session_id: str = Field(..., description="Unique UUID of the created agent session")
    status: str = Field(default="QUEUED", description="Initial execution lifecycle state")
    queue_name: str = Field(default="agents", description="Target Celery worker queue")
    priority: int = Field(default=5, description="Priority routing level (1=highest, 10=lowest)")
    task_prompt: Optional[str] = Field(default=None, description="Original instruction prompt")
    target_url: Optional[str] = Field(default=None, description="Target web address")


class AgentSession(BaseModel):
    """Detailed status and telemetry of an active or completed agent session."""
    id: str = Field(..., description="Session UUID")
    tenant_id: str = Field(..., description="Owner Tenant ID")
    task_prompt: str = Field(..., description="Execution prompt")
    target_url: Optional[str] = Field(default=None, description="Target web address")
    status: str = Field(..., description="Current lifecycle state (QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)")
    queue_name: Optional[str] = Field(default="agents", description="Worker queue name")
    priority: Optional[int] = Field(default=5, description="Queue priority")
    step_count: int = Field(default=0, description="Number of browser actions completed")
    max_steps: int = Field(default=25, description="Maximum browser steps allowed")
    current_url: Optional[str] = Field(default=None, description="Active browser URL")
    created_at: Optional[Any] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[Any] = Field(default=None, description="Last update timestamp")
    result: Optional[Any] = Field(default=None, description="Final output or execution error summary")


class TaskMetrics(BaseModel):
    """Aggregated task execution metrics across the tenant or platform."""
    total_tasks: int = Field(default=0, description="Total tasks submitted")
    queued_tasks: int = Field(default=0, description="Tasks waiting in queue")
    running_tasks: int = Field(default=0, description="Tasks currently executing in browser")
    completed_tasks: int = Field(default=0, description="Successfully completed tasks")
    failed_tasks: int = Field(default=0, description="Tasks failed or sent to DLQ")
    cancelled_tasks: int = Field(default=0, description="Tasks explicitly cancelled")
    avg_duration_seconds: float = Field(default=0.0, description="Average task completion latency")


class WorkerMetrics(BaseModel):
    """Observability telemetry for distributed Celery worker clusters."""
    active_workers: int = Field(default=0, description="Count of online worker nodes")
    queues: Dict[str, Any] = Field(default_factory=dict, description="Queue depth and processing velocity")
    total_processed: int = Field(default=0, description="Aggregate processed task counter")


class HealthStatus(BaseModel):
    """Overall system health and stateful dependency diagnostics."""
    status: str = Field(default="healthy", description="Overall cluster state (healthy, degraded, down)")
    version: str = Field(default="2.0.0", description="Agent-Bastion core release version")
    environment: str = Field(default="production", description="Active runtime environment")
    database: str = Field(default="connected", description="PostgreSQL database pool status")
    redis: str = Field(default="connected", description="Redis Celery broker status")
    workers: int = Field(default=0, description="Number of responsive Celery worker instances")


class TenantConfig(BaseModel):
    """Tenant organization registration info and rate limit quotas."""
    id: str = Field(..., description="Tenant UUID")
    name: str = Field(..., description="Organization name")
    tier: str = Field(default="PRO", description="Assigned tier (FREE, PRO, ENTERPRISE)")
    request_limit: int = Field(default=200, description="Max requests allowed per window")
    rate_window: int = Field(default=60, description="Sliding window duration in seconds")
    is_active: bool = Field(default=True, description="Whether organization account is active")
    api_key: Optional[str] = Field(default=None, description="Generated API key plaintext (only returned on creation)")


class APIKeyInfo(BaseModel):
    """API key lifecycle metadata and quota limits."""
    id: str = Field(..., description="API Key UUID")
    name: str = Field(..., description="Descriptive label for key")
    key_prefix: str = Field(..., description="First 8 characters of key for display")
    rate_limit: int = Field(default=300, description="Max requests per minute for this key")
    is_active: bool = Field(default=True, description="Active status")
    created_at: Optional[Any] = Field(default=None, description="Creation timestamp")
