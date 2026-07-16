# ============================================================
# ABSs v2.0 — Multi-Tenant AI Browser Security Proxy
# Phase 8 Verification Test Suite: Python SDK, CLI & Open Source Readiness
# Verifies Client SDK initialization, authentication/error handling, models,
# CLI command invocation, and adapter interface contracts.
# ============================================================

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from agent_bastion import (
    Client,
    AgentBastionClient,
    AgentBastionError,
    AuthenticationError,
    RateLimitError,
    TenantIsolationError,
    ConnectionError,
    TaskSubmission,
    AgentSession,
    BaseAgentAdapter,
    LangGraphAdapter,
    CrewAIAdapter,
    AutoGenAdapter,
    OpenAIAgentAdapter,
    MCPServerAdapter,
    __version__,
)
from agent_bastion.cli import main as cli_main


# ── 1. Package Structure & Import Verification ────────────────────────

def test_8_1_package_imports_and_version():
    """Verify clean top-level imports from `agent_bastion` and version assignment."""
    assert __version__ == "2.0.0"
    assert Client is not None
    assert AgentBastionClient is Client
    assert issubclass(AuthenticationError, AgentBastionError)
    assert issubclass(RateLimitError, AgentBastionError)
    assert issubclass(TenantIsolationError, AgentBastionError)


# ── 2. SDK Client Lifecycle & Error Handling Tests ────────────────────

def test_8_2_client_init_and_env_reading(monkeypatch):
    """Verify Client reads API keys and base URLs from environment when not passed explicitly."""
    monkeypatch.setenv("AGENT_BASTION_API_KEY", "abs_ak_env_test_999")
    monkeypatch.setenv("AGENT_BASTION_BASE_URL", "http://env-host.internal:8000")

    with Client() as client:
        assert client.api_key == "abs_ak_env_test_999"
        assert client.base_url == "http://env-host.internal:8000"
        assert client._default_headers["X-API-Key"] == "abs_ak_env_test_999"
        assert client._default_headers["Authorization"] == "Bearer abs_ak_env_test_999"


@patch("httpx.Client.request")
def test_8_3_sdk_create_agent_session_and_status(mock_req):
    """Verify `client.create_agent_session()` and `client.get_status()` send correct HTTP payloads."""
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "session_id": "sess-1234-5678",
        "status": "QUEUED",
        "queue_name": "agents",
        "priority": 5,
    }
    mock_req.return_value = mock_response

    client = Client(api_key="abs_ak_test", base_url="http://localhost:8000")
    res = client.create_agent_session(
        task_prompt="Navigate and extract headers",
        target_url="https://example.com",
        priority=5,
    )

    assert res["session_id"] == "sess-1234-5678"
    assert res["status"] == "QUEUED"
    mock_req.assert_called_once_with(
        method="POST",
        url="/api/v1/agents",
        params=None,
        json={"task_prompt": "Navigate and extract headers", "target_url": "https://example.com", "priority": 5, "max_retries": 3},
    )

    # Test get_status
    mock_response_status = MagicMock()
    mock_response_status.status_code = 200
    mock_response_status.json.return_value = {
        "id": "sess-1234-5678",
        "tenant_id": "tenant-01",
        "status": "COMPLETED",
        "step_count": 4,
        "current_url": "https://example.com/done",
    }
    mock_req.reset_mock()
    mock_req.return_value = mock_response_status

    status_res = client.get_status("sess-1234-5678")
    assert status_res["status"] == "COMPLETED"
    assert status_res["step_count"] == 4
    mock_req.assert_called_once_with(
        method="GET",
        url="/api/v1/agents/sess-1234-5678",
        params=None,
        json=None,
    )


@patch("httpx.Client.request")
def test_8_4_sdk_error_mapping(mock_req):
    """Verify SDK maps HTTP status codes (401, 403, 429, 500) directly to custom exception classes."""
    client = Client(api_key="abs_ak_invalid")

    # 401 AuthenticationError
    mock_response_401 = MagicMock()
    mock_response_401.status_code = 401
    mock_req.return_value = mock_response_401
    with pytest.raises(AuthenticationError, match="Authentication failed"):
        client.check_health()

    # 403 TenantIsolationError
    mock_response_403 = MagicMock()
    mock_response_403.status_code = 403
    mock_req.return_value = mock_response_403
    with pytest.raises(TenantIsolationError, match="Access denied"):
        client.get_status("some-other-tenant-sess")

    # 429 RateLimitError
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429
    mock_response_429.headers = {"Retry-After": "45"}
    mock_req.return_value = mock_response_429
    with pytest.raises(RateLimitError) as exc_info:
        client.create_agent_session("Test flood")
    assert exc_info.value.retry_after == 45


# ── 3. CLI Subcommand Execution Tests ─────────────────────────────────

@patch("sys.argv", ["agent-bastion", "version"])
def test_8_5_cli_version_command(capsys):
    """Verify CLI `agent-bastion version` outputs correct string and exit code 0."""
    ret = cli_main()
    assert ret == 0
    captured = capsys.readouterr()
    assert "Agent-Bastion CLI v2.0.0" in captured.out


@patch("sys.argv", ["agent-bastion", "init"])
def test_8_6_cli_init_command(capsys, tmp_path, monkeypatch):
    """Verify CLI `agent-bastion init` initializes `.env` template and config folder."""
    monkeypatch.chdir(tmp_path)
    ret = cli_main()
    assert ret == 0
    assert (tmp_path / ".env").exists()
    assert "ENV=production" in (tmp_path / ".env").read_text(encoding="utf-8")


@patch("agent_bastion.client.Client._request")
@patch("sys.argv", ["agent-bastion", "deploy", "--prompt", "Extract table from URL", "--url", "https://table.com", "--priority", "2"])
def test_8_7_cli_deploy_command(mock_request, capsys):
    """Verify CLI `agent-bastion deploy` parses flags accurately and invokes client."""
    mock_request.return_value = {"session_id": "cli-sess-999", "status": "QUEUED", "queue_name": "priority_agents"}
    ret = cli_main()
    assert ret == 0
    mock_request.assert_called_once()
    assert mock_request.call_args[0][0] == "POST"
    assert mock_request.call_args[0][1] == "/api/v1/agents"
    captured = capsys.readouterr()
    assert "cli-sess-999" in captured.out


# ── 4. Extensible Adapter Interfaces (`Task 7`) ───────────────────────

def test_8_8_extensible_adapters_interface_validation():
    """Verify LangGraph, CrewAI, AutoGen, OpenAI, and MCP adapter serialization payloads."""
    client = Client()
    lg = LangGraphAdapter(client, graph_spec={"nodes": ["browser_navigate"]})
    assert lg.to_session_payload()["adapter_type"] == "langgraph"
    assert lg.to_session_payload()["graph_spec"]["nodes"] == ["browser_navigate"]

    crew = CrewAIAdapter(client, crew_config={"role": "Web Researcher"})
    assert crew.to_session_payload()["adapter_type"] == "crewai"

    autogen = AutoGenAdapter(client, agents=["AssistantAgent", "UserProxy"])
    assert autogen.to_session_payload()["adapter_type"] == "autogen"
    assert autogen.to_session_payload()["agent_count"] == 2

    openai_agent = OpenAIAgentAdapter(client, assistant_id="asst_123456")
    assert openai_agent.to_session_payload()["adapter_type"] == "openai_agent"
    assert openai_agent.to_session_payload()["assistant_id"] == "asst_123456"

    mcp = MCPServerAdapter(client, tools_whitelist=["browser_click", "browser_extract"])
    assert mcp.to_session_payload()["adapter_type"] == "mcp_server"
    assert "browser_click" in mcp.to_session_payload()["tools_whitelist"]
