# ============================================================
# ABSs v2.0 — Multi-Tenant AI Browser Security Proxy
# Development & Deployment Makefile
# ============================================================

.PHONY: help build up down restart logs status \
        up-full up-dev clean seed test shell-api shell-worker

# ── Defaults ──────────────────────────────────────────────────
COMPOSE = docker compose
ENV_FILE = .env

# ── Help ──────────────────────────────────────────────────────
help: ## Show this help
	@echo ""
	@echo "  ABSs v2.0 — Docker Commands"
	@echo "  ════════════════════════════════════════════"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Build ─────────────────────────────────────────────────────
build: ## Build all Docker images
	$(COMPOSE) build

build-no-cache: ## Rebuild all images from scratch
	$(COMPOSE) build --no-cache

# ── Start / Stop ──────────────────────────────────────────────
up: ## Start core services (API, workers, dashboard, infra)
	$(COMPOSE) up --build -d

up-full: ## Start everything including Flower monitoring
	$(COMPOSE) --profile monitoring up --build -d

up-dev: ## Start everything including attack test server
	$(COMPOSE) --profile dev --profile monitoring up --build -d

down: ## Stop all services
	$(COMPOSE) --profile monitoring --profile dev down

down-clean: ## Stop all services and remove volumes (DESTRUCTIVE)
	$(COMPOSE) --profile monitoring --profile dev down -v

restart: ## Restart all services
	$(COMPOSE) --profile monitoring --profile dev restart

# ── Logs ──────────────────────────────────────────────────────
logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-api: ## Tail API logs
	$(COMPOSE) logs -f --tail=100 api

logs-agent: ## Tail agent worker logs
	$(COMPOSE) logs -f --tail=100 worker-agent

logs-xai: ## Tail XAI worker logs
	$(COMPOSE) logs -f --tail=100 worker-xai

# ── Status ────────────────────────────────────────────────────
status: ## Show service status
	$(COMPOSE) ps -a

health: ## Check health of all services
	@echo "── Service Health ──────────────────────────"
	@$(COMPOSE) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# ── Database ──────────────────────────────────────────────────
db-shell: ## Open PostgreSQL shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-abs_user} -d $${POSTGRES_DB:-abs_db}

# ── Debug Shells ──────────────────────────────────────────────
shell-api: ## Open shell in API container
	$(COMPOSE) exec api /bin/bash

shell-worker: ## Open shell in agent worker container
	$(COMPOSE) exec worker-agent /bin/bash

# ── Testing ───────────────────────────────────────────────────
test: ## Run pytest (locally, not in Docker)
	pytest src/tests/ -v

# ── Setup ─────────────────────────────────────────────────────
init: ## First-time setup: copy env template
	@if [ ! -f $(ENV_FILE) ]; then \
		cp .env.docker $(ENV_FILE); \
		echo "✅ Created .env from .env.docker — edit it with your API keys!"; \
	else \
		echo "⚠️  .env already exists. Skipping."; \
	fi

# ── Cleanup ───────────────────────────────────────────────────
clean: ## Remove dangling images and build cache
	docker image prune -f
	docker builder prune -f
