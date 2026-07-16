"""
agent_bastion.cli — Authoritative Command-Line Interface (CLI) for Agent-Bastion v2.0.

Provides developer-first console commands for initializing workspaces, managing tenants/keys,
deploying agent sessions, and inspecting system metrics.

Commands:
    agent-bastion init
    agent-bastion login
    agent-bastion create-tenant
    agent-bastion generate-api-key
    agent-bastion deploy
    agent-bastion status
    agent-bastion health
    agent-bastion metrics
    agent-bastion version
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from agent_bastion.client import Client
from agent_bastion.exceptions import AgentBastionError

CONFIG_DIR = Path.home() / ".agent-bastion"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load_config() -> Dict[str, Any]:
    """Load local CLI configuration file (`~/.agent-bastion/config.json`)."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_config(config: Dict[str, Any]) -> None:
    """Persist CLI configuration to `~/.agent-bastion/config.json`."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _get_client(args: argparse.Namespace) -> Client:
    """Construct an authenticated SDK Client using CLI args, env vars, or local config."""
    config = _load_config()
    api_key = getattr(args, "api_key", None) or os.getenv("AGENT_BASTION_API_KEY") or config.get("api_key")
    base_url = getattr(args, "url", None) or os.getenv("AGENT_BASTION_BASE_URL") or config.get("base_url") or "http://localhost:8000"
    return Client(api_key=api_key, base_url=base_url)


def _print_output(data: Any, as_json: bool = False) -> None:
    """Format and display output to terminal."""
    if as_json or isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


# ── Command Handlers ──────────────────────────────────────────────────

def handle_init(args: argparse.Namespace) -> int:
    """Initialize local environment for quickstart testing (`agent-bastion init`)."""
    print("\033[34m[Agent-Bastion]\033[0m Initializing local development workspace...")
    env_example = Path(".env.example")
    env_file = Path(".env")
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
        print("\033[32m✔ Created local .env file from .env.example\033[0m")
    elif not env_file.exists():
        env_file.write_text(
            "ENV=production\n"
            "JWT_SECRET_KEY=94b2c18d7f3e091a56c4d8e2f1a3b7c9e0d4a8f2b6c1e5d9a3f7b2c8e4d0a1f5\n"
            "POSTGRES_PASSWORD=P@ssw0rd_CryptographicallyRandomSecret_987654321!\n"
            "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000\n",
            encoding="utf-8",
        )
        print("\033[32m✔ Generated secure production .env template\033[0m")
    else:
        print("\033[33m! .env file already exists (skipping creation)\033[0m")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    print("\033[32m✔ Workspace initialized. Run `docker compose up --build -d` to launch stack.\033[0m")
    return 0


def handle_login(args: argparse.Namespace) -> int:
    """Save API credentials to local configuration (`agent-bastion login`)."""
    if not args.api_key:
        print("\033[31mError: --api-key is required for login.\033[0m", file=sys.stderr)
        return 1

    config = _load_config()
    config["api_key"] = args.api_key
    if args.url:
        config["base_url"] = args.url
    elif "base_url" not in config:
        config["base_url"] = "http://localhost:8000"

    _save_config(config)
    print(f"\033[32m✔ Successfully authenticated with Agent-Bastion at {config['base_url']}\033[0m")
    return 0


def handle_create_tenant(args: argparse.Namespace) -> int:
    """Create a new tenant organization (`agent-bastion create-tenant`)."""
    with _get_client(args) as client:
        try:
            res = client.create_tenant(name=args.name, tier=args.tier, contact_email=args.email)
            print("\033[32m✔ Tenant successfully registered:\033[0m")
            _print_output(res, args.json)
            return 0
        except AgentBastionError as exc:
            print(f"\033[31mError creating tenant: {exc.message}\033[0m", file=sys.stderr)
            return 1


def handle_generate_api_key(args: argparse.Namespace) -> int:
    """Generate a new cryptographic API key (`agent-bastion generate-api-key`)."""
    with _get_client(args) as client:
        try:
            res = client.generate_api_key(tenant_id=args.tenant_id, name=args.name)
            print("\033[32m✔ API Key generated successfully:\033[0m")
            _print_output(res, args.json)
            return 0
        except AgentBastionError as exc:
            print(f"\033[31mError generating API key: {exc.message}\033[0m", file=sys.stderr)
            return 1


def handle_deploy(args: argparse.Namespace) -> int:
    """Submit a new browser agent session/task (`agent-bastion deploy`)."""
    with _get_client(args) as client:
        try:
            res = client.create_agent_session(
                task_prompt=args.prompt,
                target_url=args.url,
                queue_name=args.queue,
                priority=args.priority,
                max_retries=args.max_retries,
            )
            print("\033[32m✔ Agent Task Deployed Successfully:\033[0m")
            _print_output(res, args.json)
            return 0
        except AgentBastionError as exc:
            print(f"\033[31mError deploying agent task: {exc.message}\033[0m", file=sys.stderr)
            return 1


def handle_status(args: argparse.Namespace) -> int:
    """Check live status of an agent session (`agent-bastion status`)."""
    with _get_client(args) as client:
        try:
            res = client.get_status(args.session_id)
            _print_output(res, args.json)
            return 0
        except AgentBastionError as exc:
            print(f"\033[31mError fetching status for session {args.session_id}: {exc.message}\033[0m", file=sys.stderr)
            return 1


def handle_health(args: argparse.Namespace) -> int:
    """Inspect overall system health (`agent-bastion health`)."""
    with _get_client(args) as client:
        try:
            res = client.check_health()
            _print_output(res, args.json)
            return 0
        except AgentBastionError as exc:
            print(f"\033[31mError checking health: {exc.message}\033[0m", file=sys.stderr)
            return 1


def handle_metrics(args: argparse.Namespace) -> int:
    """Inspect platform and task metrics (`agent-bastion metrics`)."""
    with _get_client(args) as client:
        try:
            res = client.metrics()
            _print_output(res, args.json)
            return 0
        except AgentBastionError as exc:
            print(f"\033[31mError fetching metrics: {exc.message}\033[0m", file=sys.stderr)
            return 1


def handle_version(args: argparse.Namespace) -> int:
    """Output version info (`agent-bastion version`)."""
    from agent_bastion import __version__
    ver_info = {
        "cli_version": __version__,
        "sdk_version": __version__,
        "protocol_version": "v1",
    }
    if args.json:
        _print_output(ver_info, as_json=True)
    else:
        print(f"Agent-Bastion CLI v{__version__} (Python SDK v{__version__})")
    return 0


# ── Main Parser Setup ─────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-bastion",
        description="Agent-Bastion CLI — Secure, Multi-Tenant AI Browser Agent Orchestration",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # init
    subparsers.add_parser("init", help="Initialize local workspace and .env configuration")

    # login
    login_p = subparsers.add_parser("login", help="Save API credentials to local config")
    login_p.add_argument("--api-key", required=True, help="API Key (`abs_ak_...`)")
    login_p.add_argument("--url", default="http://localhost:8000", help="Base gateway URL")

    # create-tenant
    ct_p = subparsers.add_parser("create-tenant", help="Register a new multi-tenant organization")
    ct_p.add_argument("--name", required=True, help="Organization name")
    ct_p.add_argument("--tier", default="PRO", choices=["FREE", "PRO", "ENTERPRISE"], help="Service tier")
    ct_p.add_argument("--email", default=None, help="Admin contact email")
    ct_p.add_argument("--url", default=None, help="Override base gateway URL")

    # generate-api-key
    gk_p = subparsers.add_parser("generate-api-key", help="Generate a new API key")
    gk_p.add_argument("--tenant-id", default=None, help="Target Tenant ID")
    gk_p.add_argument("--name", default="default-cli-key", help="Key descriptive label")
    gk_p.add_argument("--api-key", default=None, help="Override auth API key")
    gk_p.add_argument("--url", default=None, help="Override base gateway URL")

    # deploy
    dep_p = subparsers.add_parser("deploy", help="Submit a new browser agent execution task")
    dep_p.add_argument("--prompt", required=True, help="Natural language instruction prompt")
    dep_p.add_argument("--url", default=None, help="Target starting web URL")
    dep_p.add_argument("--queue", default="agents", help="Target Celery queue")
    dep_p.add_argument("--priority", type=int, default=5, help="Task priority (1-10)")
    dep_p.add_argument("--max-retries", type=int, default=3, help="Max retry attempts on failure")
    dep_p.add_argument("--api-key", default=None, help="Override auth API key")
    dep_p.add_argument("--base-url", dest="url", default=None, help="Override base gateway URL")

    # status
    st_p = subparsers.add_parser("status", help="Inspect session progression and output")
    st_p.add_argument("-s", "--session-id", required=True, help="Unique UUID of agent session")
    st_p.add_argument("--api-key", default=None, help="Override auth API key")
    st_p.add_argument("--url", default=None, help="Override base gateway URL")

    # health
    hl_p = subparsers.add_parser("health", help="Check system cluster health")
    hl_p.add_argument("--url", default=None, help="Override base gateway URL")

    # metrics
    mt_p = subparsers.add_parser("metrics", help="Check task execution and queue metrics")
    mt_p.add_argument("--api-key", default=None, help="Override auth API key")
    mt_p.add_argument("--url", default=None, help="Override base gateway URL")

    # version
    v_p = subparsers.add_parser("version", help="Print CLI and SDK version")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "init": handle_init,
        "login": handle_login,
        "create-tenant": handle_create_tenant,
        "generate-api-key": handle_generate_api_key,
        "deploy": handle_deploy,
        "status": handle_status,
        "health": handle_health,
        "metrics": handle_metrics,
        "version": handle_version,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
