# Agent-Bastion 🛡️🌐
**The Easiest Way to Securely Deploy AI Agents in Production.**

[![Production Quality](https://img.shields.io/badge/Quality-Production%20Grade-00C853.svg)](https://github.com/Ashitpatel001/Agent-Bastion)
[![Version](https://img.shields.io/badge/Version-2.0.0-0086X3.svg)](https://pypi.org/project/agent-bastion/)
[![Python SDK](https://img.shields.io/badge/Python%20SDK->=3.11-3776AB.svg?logo=python&logoColor=white)](https://pypi.org/project/agent-bastion/)
[![Docker](https://img.shields.io/badge/Docker-Zero--Trust%20Sandboxed-2496ED.svg?logo=docker&logoColor=white)](docs/DEPLOYMENT_GUIDE.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Agent-Bastion is an authoritative, zero-trust **Multi-Tenant AI Browser Security Proxy & Orchestration Platform** that enables developers and enterprises to run autonomous web automation agents without risking credential theft, SSRF attacks, excessive bandwidth billing, or data exfiltration.

---

## 🏗️ System Architecture

```
                       ┌─────────────────────────────────────────────────────────┐
                       │                   External Clients                      │
                       │    (Python SDK / CLI / LangGraph / CrewAI / AutoGen)    │
                       └───────────────────────────┬─────────────────────────────┘
                                                   │ HTTPS / API Key (`X-API-Key`)
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Caddy Edge Reverse Proxy (Port 80 / 443)                                                         │
│   ├── Coraza WAF (OWASP Core Rule Set + SSRF / SQLi / XSS Blocking)                              │
│   └── fail2ban Host IPS (Brute Force / DDoS / Scanner Auto-Jail)                                 │
└──────────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                   │ Internal Bridge (`abs-backend` Network)
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Gateway Core (Internal Port 8000)                                                        │
│   ├── Tenant Authentication & Cryptographic API Key Verification (`passlib` + `python-jose`)     │
│   ├── Multi-Tenant Quota & Sliding-Window Rate Limiter (Redis-backed Token Bucket)               │
│   └── InputSanitizationLayer (`bleach` + URL Hostname Enforcement + Honeytoken Injection)        │
└───────────────────────┬──────────────────────────────────────────┬───────────────────────────────┘
                        │ Async Task Enqueue                       │ SQL Audit Logging
                        ▼                                          ▼
┌───────────────────────────────────────────────┐  ┌───────────────────────────────────────────────┐
│ Distributed Worker Cluster (`Celery` + Redis) │  │ PostgreSQL 15 Database (Internal Port 5432)   │
│   ├── Priority Queue (`priority_agents`)      │  │   ├── Isolated Tenant Boundaries (`tenant_id`)│
│   ├── Standard Queue (`agents`)               │  │   ├── Encrypted Audit Trail (`SecurityLog`)   │
│   └── Dead-Letter Queue (`dlq`)               │  │   └── Quota & Session Storage                 │
└───────────────────────┬───────────────────────┘  └───────────────────────────────────────────────┘
                        │ Isolated Browser Sandboxes
                        ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Ephemeral Chromium Sandboxes (`seccomp:unconfined` + Hardened Network Boundaries)                │
│   └── Outbound Network Filtering & Deception Honeytokens                                         │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 5-Minute Quickstart Workflow

Can a developer securely deploy their first AI agent in under five minutes? **Yes.**

### Step 1: Launch the Production Stack
Clone the repository and spin up the complete zero-trust platform using Docker Compose:
```bash
git clone https://github.com/Ashitpatel001/Agent-Bastion.git
cd Agent-Bastion
cp .env.example .env
docker compose up --build -d
```

### Step 2: Install the Python SDK & CLI
Install the official package directly via `pip`:
```bash
pip install agent-bastion
```

### Step 3: Initialize & Provision Your Tenant
Use the CLI to register your organization and generate an administrative API key:
```bash
# Register tenant
agent-bastion create-tenant --name "Acme AI Labs" --tier ENTERPRISE

# Save API Key to local profile
agent-bastion login --api-key "abs_ak_prod_your_generated_key_here"
```

### Step 4: Submit Your First Autonomous Task
Run a web extraction task directly from your terminal:
```bash
agent-bastion deploy --prompt "Extract top 3 technology headlines" --url "https://news.ycombinator.com" --priority 1
```

### Step 5: Monitor Execution Progression
Inspect live step execution and retrieve extracted output:
```bash
agent-bastion status --session-id "<YOUR_SESSION_UUID>"
```

---

## 🐍 Python SDK (`from agent_bastion import Client`)

Agent-Bastion provides a clean, Pythonic SDK designed for synchronous and asynchronous execution:

```python
from agent_bastion import Client, AgentBastionError

# Initialize client (automatically reads AGENT_BASTION_API_KEY env var)
with Client(api_key="abs_ak_prod_123456") as client:
    try:
        # Submit task
        session = client.create_agent_session(
            task_prompt="Navigate to company portal and audit login link responsiveness",
            target_url="https://example.com",
            priority=3,
            max_retries=3,
        )
        print(f"Task Enqueued: {session['session_id']} (Queue: {session['queue_name']})")

        # Check progression
        status = client.get_status(session["session_id"])
        print(f"Status: {status['status']} | Steps Completed: {status['step_count']}")

        # Retrieve cluster observability metrics
        metrics = client.metrics()
        print(f"Total Processed Tasks: {metrics.get('total_tasks')}")

    except AgentBastionError as exc:
        print(f"SDK Exception [{exc.status_code}]: {exc.message}")
```

---

## 🖥️ CLI Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `agent-bastion init` | Initialize local workspace (`.env` & configuration) | `agent-bastion init` |
| `agent-bastion login` | Save API credentials locally to `~/.agent-bastion/` | `agent-bastion login --api-key abs_ak_...` |
| `agent-bastion create-tenant`| Register new multi-tenant organization | `agent-bastion create-tenant --name Acme --tier PRO` |
| `agent-bastion generate-api-key` | Generate cryptographic API key for workers | `agent-bastion generate-api-key --name worker-key` |
| `agent-bastion deploy` | Enqueue a new browser automation task | `agent-bastion deploy --prompt "Audit site" --url "https://..."`|
| `agent-bastion status` | Inspect task progression, step count, and result | `agent-bastion status -s <SESSION_UUID>` |
| `agent-bastion health` | Check database, redis, and worker cluster health | `agent-bastion health` |
| `agent-bastion metrics` | Inspect task queues and worker telemetry | `agent-bastion metrics` |
| `agent-bastion version` | Display CLI and SDK release versions | `agent-bastion version` |

---

## 🔌 Extensible Adapter Interfaces (Future Compatibility)

Agent-Bastion v2.0 includes extensible adapter interfaces (`src/agent_bastion/adapters.py`) designed to seamlessly bridge major AI agent orchestration frameworks with zero-trust sandboxed workers:

- **LangGraph** (`LangGraphAdapter`): Route graph node execution and checkpointers through isolated browser workers.
- **CrewAI** (`CrewAIAdapter`): Delegate multi-agent research crews (`agents`, `tasks`) to priority queues.
- **AutoGen** (`AutoGenAdapter`): Secure conversable assistant and user proxy web execution loops.
- **OpenAI Agents** (`OpenAIAgentAdapter`): Bridge Assistant / Swarm tool calls to WAF-inspected endpoints.
- **MCP Servers** (`MCPServerAdapter`): Expose Agent-Bastion browser actions via standard Model Context Protocol JSON-RPC.

---

## 📚 Comprehensive Documentation

Explore our production-grade guides in the `docs/` directory:

- [⚡ Quickstart Guide](docs/QUICKSTART_GUIDE.md) — Step-by-step 5-minute onboarding tutorial.
- [🛠️ Installation Guide](docs/INSTALLATION_GUIDE.md) — Package installation, virtual environments, and Docker setups.
- [🚀 Deployment Guide](docs/DEPLOYMENT_GUIDE.md) — VPS provisioning, DNS, Caddy SSL, and fail2ban host hardening.
- [🔒 Security Guide](docs/SECURITY_GUIDE.md) — Deep dive into WAF rules, honeytokens, input sanitization, and tenant isolation.
- [📖 SDK Guide](docs/SDK_GUIDE.md) — Comprehensive API reference for `agent_bastion.Client` and models.
- [⌨️ CLI Guide](docs/CLI_GUIDE.md) — Full manual for `agent-bastion` console commands and exit codes.
- [🏛️ Architecture Guide](docs/ARCHITECTURE_GUIDE.md) — Multi-layer design, queue topologies, and zero-trust boundaries.
- [❓ FAQ](docs/FAQ.md) — Frequently asked questions on LLM providers, rate limits, and self-hosting.
- [🤝 Contributing Guide](CONTRIBUTING.md) — Developer setup, `ruff` formatting, type checking, and PR rules.

---

## 🛡️ Security Guarantees

Agent-Bastion enforces strict defense-in-depth across every boundary:
1. **Zero Host Port Exposure**: Only Caddy reverse proxy (`:80/:443`) and Grafana (`:3001`) are exposed. Database (`:5432`), Redis (`:6379`), and API Gateway (`:8000`) communicate exclusively over internal Docker bridge networks (`Task 7.5`).
2. **Hardened Container Runtimes**: All API and worker containers run as non-root user (`appuser`, UID 10001) (`Task 7.3`).
3. **Automated Threat Mitigation**: Coraza WAF blocks injection attacks while `fail2ban` dynamically jails scanning or brute-forcing IP addresses at the host kernel table (`Task 7.2 & 7.4`).
4. **Mandatory Tenant Isolation**: Every PostgreSQL query dynamically filters by `tenant_id`, guaranteeing cross-tenant data boundaries (`Task 4.1`).

---

## 📄 License

Agent-Bastion is open-source software licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
