"""
agent_bastion — Production Python SDK & Client Library for Agent-Bastion v2.0.

The easiest way to securely deploy AI browser automation agents in production.
Provides full multi-tenant isolation, real-time observability, and zero-trust security.
"""

from agent_bastion.client import Client, AgentBastionClient
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
from agent_bastion.adapters import (
    BaseAgentAdapter,
    LangGraphAdapter,
    CrewAIAdapter,
    AutoGenAdapter,
    OpenAIAgentAdapter,
    MCPServerAdapter,
)

__version__ = "2.0.0"
__all__ = [
    "Client",
    "AgentBastionClient",
    "AgentBastionError",
    "AuthenticationError",
    "RateLimitError",
    "TenantIsolationError",
    "TaskExecutionError",
    "ConnectionError",
    "TaskSubmission",
    "AgentSession",
    "TaskMetrics",
    "WorkerMetrics",
    "HealthStatus",
    "TenantConfig",
    "APIKeyInfo",
    "BaseAgentAdapter",
    "LangGraphAdapter",
    "CrewAIAdapter",
    "AutoGenAdapter",
    "OpenAIAgentAdapter",
    "MCPServerAdapter",
    "__version__",
]
