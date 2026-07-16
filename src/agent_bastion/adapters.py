"""
agent_bastion.adapters — Extensible interfaces for third-party AI agent frameworks and MCP servers.

Designed for future compatibility with:
- Browser agents
- LangGraph
- CrewAI
- AutoGen
- OpenAI Agents
- MCP Servers

NOTE: Per Phase 8 architectural guidelines, only abstract extensible interfaces are defined here.
Actual third-party framework runtime integrations will implement these contracts in future releases.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List


class BaseAgentAdapter(ABC):
    """
    Abstract base interface for connecting external agent frameworks to the Agent-Bastion proxy.
    All custom or third-party adapters MUST inherit from this base class.
    """

    def __init__(self, client: Any, tenant_id: Optional[str] = None):
        """
        Initialize the adapter with an active Agent-Bastion Client instance.

        Args:
            client: An initialized `agent_bastion.Client` instance.
            tenant_id: Optional tenant identifier override.
        """
        self.client = client
        self.tenant_id = tenant_id

    @abstractmethod
    async def execute(self, prompt: str, target_url: Optional[str] = None, **kwargs: Any) -> Any:
        """
        Execute an autonomous task using the framework's runtime engine while proxying browser actions
        and network calls through Agent-Bastion's security and WAF inspection layers.

        Args:
            prompt: Natural language instruction for the agent.
            target_url: Optional starting URL.
            **kwargs: Framework-specific execution parameters.

        Returns:
            Execution output or status summary.
        """
        pass

    @abstractmethod
    def to_session_payload(self) -> Dict[str, Any]:
        """
        Serialize the adapter's configuration into a valid Agent-Bastion API session submission dictionary.
        """
        pass


class LangGraphAdapter(BaseAgentAdapter):
    """
    Extensible interface for LangGraph state graphs and checkpointer execution loops.
    Allows LangGraph nodes to execute browser actions safely within isolated Agent-Bastion worker sandboxes.
    """

    def __init__(self, client: Any, graph_spec: Optional[Dict[str, Any]] = None, checkpointer: Any = None, **kwargs: Any):
        super().__init__(client, **kwargs)
        self.graph_spec = graph_spec or {}
        self.checkpointer = checkpointer

    async def execute(self, prompt: str, target_url: Optional[str] = None, **kwargs: Any) -> Any:
        raise NotImplementedError("LangGraphAdapter execution engine will be implemented in a future release.")

    def to_session_payload(self) -> Dict[str, Any]:
        return {
            "adapter_type": "langgraph",
            "graph_spec": self.graph_spec,
            "has_checkpointer": self.checkpointer is not None,
        }


class CrewAIAdapter(BaseAgentAdapter):
    """
    Extensible interface for CrewAI multi-agent crews (`agents`, `tasks`, and `process`).
    Allows CrewAI agents to delegate web research and browser interaction tasks to Agent-Bastion workers.
    """

    def __init__(self, client: Any, crew_config: Optional[Dict[str, Any]] = None, **kwargs: Any):
        super().__init__(client, **kwargs)
        self.crew_config = crew_config or {}

    async def execute(self, prompt: str, target_url: Optional[str] = None, **kwargs: Any) -> Any:
        raise NotImplementedError("CrewAIAdapter execution engine will be implemented in a future release.")

    def to_session_payload(self) -> Dict[str, Any]:
        return {
            "adapter_type": "crewai",
            "crew_config": self.crew_config,
        }


class AutoGenAdapter(BaseAgentAdapter):
    """
    Extensible interface for AutoGen conversable agents (`AssistantAgent`, `UserProxyAgent`).
    Routes AutoGen code/browser execution attempts through Agent-Bastion's zero-trust sandboxes.
    """

    def __init__(self, client: Any, agents: Optional[List[Any]] = None, **kwargs: Any):
        super().__init__(client, **kwargs)
        self.agents = agents or []

    async def execute(self, prompt: str, target_url: Optional[str] = None, **kwargs: Any) -> Any:
        raise NotImplementedError("AutoGenAdapter execution engine will be implemented in a future release.")

    def to_session_payload(self) -> Dict[str, Any]:
        return {
            "adapter_type": "autogen",
            "agent_count": len(self.agents),
        }


class OpenAIAgentAdapter(BaseAgentAdapter):
    """
    Extensible interface for OpenAI Assistant / Swarm agents.
    Provides function calling / tool definitions that safely bridge OpenAI models to Agent-Bastion browser tools.
    """

    def __init__(self, client: Any, assistant_id: Optional[str] = None, **kwargs: Any):
        super().__init__(client, **kwargs)
        self.assistant_id = assistant_id

    async def execute(self, prompt: str, target_url: Optional[str] = None, **kwargs: Any) -> Any:
        raise NotImplementedError("OpenAIAgentAdapter execution engine will be implemented in a future release.")

    def to_session_payload(self) -> Dict[str, Any]:
        return {
            "adapter_type": "openai_agent",
            "assistant_id": self.assistant_id,
        }


class MCPServerAdapter(BaseAgentAdapter):
    """
    Extensible interface for Model Context Protocol (MCP) server execution and tool invocation.
    Enables external LLM clients to discover and execute Agent-Bastion WAF-protected browser tools via standard MCP JSON-RPC.
    """

    def __init__(self, client: Any, tools_whitelist: Optional[List[str]] = None, **kwargs: Any):
        super().__init__(client, **kwargs)
        self.tools_whitelist = tools_whitelist or ["browser_navigate", "browser_click", "browser_extract"]

    async def execute(self, prompt: str, target_url: Optional[str] = None, **kwargs: Any) -> Any:
        raise NotImplementedError("MCPServerAdapter execution engine will be implemented in a future release.")

    def to_session_payload(self) -> Dict[str, Any]:
        return {
            "adapter_type": "mcp_server",
            "tools_whitelist": self.tools_whitelist,
        }
