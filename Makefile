# ==============================================================================
# Agent-Bastion v2.0 — Production Layer For Autonomous AI Agents
# Universal Makefile Commands
# ==============================================================================

.PHONY: help init build up up-dev up-monitoring up-security down restart logs status shell-api shell-worker test clean

COMPOSE = docker compose
ENV_FILE = .env

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Show available commands
	@echo ""
	@echo "  Agent-Bastion v2.0 — Docker & Developer Commands"
	@echo "  ══════════════════════════════════════════════════════════════"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Setup & Onboarding ────────────────────────────────────────────────────────
init: ## First-time setup: create .env from .env.example
	@if [ ! -f $(ENV_FILE) ]; then \
		cp .env.example $(ENV_FILE); \
		echo "✅ Created .env from .env.example!"; \
	else \
		echo "ℹ️  .env already exists. Skipping."; \
	fi

# ── Local Development Mode (3-Minute Setup) ───────────────────────────────────
up-dev: init ## Start Local Development Mode (Live reload on http://localhost)
	$(COMPOSE) -f docker-compose.dev.yml up --build -d
	@echo "🚀 Local Development Stack running at http://localhost"

# ── Production Mode ───────────────────────────────────────────────────────────
up: init ## Start Core Production Mode
	$(COMPOSE) up --build -d
	@echo "🚀 Production Core Stack running"

up-monitoring: init ## Start Production Mode + Monitoring (Prometheus, Loki, Grafana, Flower)
	$(COMPOSE) --profile monitoring up --build -d
	@echo "📊 Monitoring Stack running. Grafana at http://localhost:3001"

up-security: init ## Start Production Mode + Monitoring + Security IPS (fail2ban)
	$(COMPOSE) --profile monitoring --profile security up --build -d
	@echo "🛡️ Full Security & Monitoring Stack running"

# ── Stop / Teardown ───────────────────────────────────────────────────────────
down: ## Stop all services across both Dev and Prod profiles
	$(COMPOSE) --profile monitoring --profile security down
	$(COMPOSE) -f docker-compose.dev.yml down

down-clean: ## Stop all services and remove volumes (DESTRUCTIVE)
	$(COMPOSE) --profile monitoring --profile security down -v
	$(COMPOSE) -f docker-compose.dev.yml down -v

restart: ## Restart currently running containers
	$(COMPOSE) restart

# ── Logs & Status ─────────────────────────────────────────────────────────────
logs: ## Tail logs from all containers
	$(COMPOSE) logs -f --tail=100

logs-api: ## Tail API Gateway logs
	$(COMPOSE) logs -f --tail=100 api

logs-workers: ## Tail Celery agent/xai worker logs
	$(COMPOSE) logs -f --tail=100 worker-agent worker-xai

status: ## Show container status
	$(COMPOSE) ps -a

# ── Debug & Shell Access ──────────────────────────────────────────────────────
shell-api: ## Open Bash shell in API container
	$(COMPOSE) exec api /bin/bash

shell-worker: ## Open Bash shell in agent worker container
	$(COMPOSE) exec worker-agent /bin/bash

db-shell: ## Open PostgreSQL interactive shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-abs_user} -d $${POSTGRES_DB:-abs_db}

# ── Verification & Testing ────────────────────────────────────────────────────
test: ## Run local automated test suite
	python -m pytest src/tests/ -v

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove dangling images and build cache
	docker image prune -f
	docker builder prune -f
