# ============================================================
# ABSs v2.0 — Multi-Tenant AI Browser Security Proxy
# Phase 7 Verification Test Suite: Infrastructure Hardening
# Verifies Caddy Reverse Proxy, Coraza WAF, Security Headers,
# fail2ban IPS, Network Isolation, and Production Environment Validation
# ============================================================

import os
import sys
import yaml
import pytest

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from api.config import Settings


def test_7_1_caddyfile_routing_and_structure():
    """
    Verify Caddyfile reverse proxy configuration (`Caddyfile`) routes /api/* -> FastAPI
    and /* -> Next.js frontend with proper real IP headers and access logging (Task 7.1).
    """
    caddyfile_path = os.path.join(PROJECT_ROOT, "Caddyfile")
    assert os.path.exists(caddyfile_path), "Caddyfile must exist in project root"

    with open(caddyfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "admin off" in content, "Caddy admin API should be disabled for security"
    assert "handle /api/*" in content, "Must define /api/* routing handle"
    assert "reverse_proxy http://api:8000" in content, "Must proxy /api/* to api:8000"
    assert "handle /*" in content, "Must define default /* routing handle"
    assert "reverse_proxy http://frontend:3000" in content, "Must proxy /* to frontend:3000"
    assert "X-Real-IP {remote_host}" in content, "Must forward X-Real-IP header"
    assert "/var/log/caddy/access.log" in content, "Must configure access logging for promtail/fail2ban ingestion"


def test_7_2_coraza_waf_crs_rules_without_prompt_injection():
    """
    Verify Coraza WAF config (`caddy/coraza.conf`) enforces OWASP CRS rules for SQLi, XSS,
    path traversal, and protocol violations, WITHOUT prompt-injection rules at WAF level (Task 7.2).
    """
    coraza_path = os.path.join(PROJECT_ROOT, "caddy", "coraza.conf")
    assert os.path.exists(coraza_path), "caddy/coraza.conf must exist"

    with open(coraza_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "SecRuleEngine On" in content, "WAF Rule Engine must be active (On)"
    assert "tx.crs_setup_version=330" in content, "Must initialize OWASP CRS setup version"
    assert "SecAuditLogFormat JSON" in content, "Audit logs should be formatted as JSON"
    assert "Prompt injections and semantic payload evaluation are strictly handled in Python app layer" in content, \
        "Must explicitly document that prompt injection rules belong in InputSanitizationLayer, not WAF"


def test_7_3_security_headers_configuration():
    """
    Verify Caddyfile defines comprehensive security headers (HSTS, CSP, X-Frame-Options,
    Referrer-Policy, Permissions-Policy, Server removal) (Task 7.3).
    """
    caddyfile_path = os.path.join(PROJECT_ROOT, "Caddyfile")
    with open(caddyfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"' in content
    assert 'X-Frame-Options "DENY"' in content
    assert 'X-Content-Type-Options "nosniff"' in content
    assert "Content-Security-Policy" in content and "frame-ancestors 'none'" in content
    assert 'Referrer-Policy "strict-origin-when-cross-origin"' in content
    assert 'Permissions-Policy "camera=(), microphone=(), geolocation=(), browsing-topics=()"' in content
    assert "-Server" in content, "Server header must be stripped"


def test_7_4_fail2ban_jails_and_filters():
    """
    Verify fail2ban configuration (`fail2ban/jail.local` and filters) accurately enforces:
    - Auth brute force: 10 failures in 60s -> 30-min ban
    - Scanner detection: 20 404s in 60s -> 24-hr ban
    - HTTP flood: 300 req/min -> 1-hr ban (Task 7.4).
    """
    jail_path = os.path.join(PROJECT_ROOT, "fail2ban", "jail.local")
    assert os.path.exists(jail_path), "fail2ban/jail.local must exist"

    with open(jail_path, "r", encoding="utf-8") as f:
        jail_content = f.read()

    # Auth brute force check
    assert "[abs-auth]" in jail_content
    assert "maxretry = 10" in jail_content and "findtime = 60" in jail_content and "bantime  = 1800" in jail_content

    # Scanner check
    assert "[abs-scanner]" in jail_content
    assert "maxretry = 20" in jail_content and "bantime  = 86400" in jail_content

    # Flood check
    assert "[abs-flood]" in jail_content
    assert "maxretry = 300" in jail_content and "bantime  = 3600" in jail_content

    # Check filter files exist
    filter_dir = os.path.join(PROJECT_ROOT, "fail2ban", "filter.d")
    for filter_file in ["abs-auth.conf", "abs-scanner.conf", "abs-flood.conf"]:
        assert os.path.exists(os.path.join(filter_dir, filter_file)), f"Filter {filter_file} must exist"


def test_7_5_network_isolation_and_port_audit():
    """
    Verify network isolation: ONLY Caddy (80/443) and Grafana (3001) are exposed to host network across
    all compose files (`docker-compose.yml` and `docker-compose.monitoring.yml`).
    Postgres, Redis, API, Frontend, Prometheus, Loki, Flower must NOT expose host ports (Task 7.5).
    """
    core_compose_path = os.path.join(PROJECT_ROOT, "docker-compose.yml")
    with open(core_compose_path, "r", encoding="utf-8") as f:
        core_compose = yaml.safe_load(f)

    services = core_compose.get("services", {})
    # Verify core services unexposed
    for svc_name in ["postgres", "redis", "api", "frontend", "worker-agent", "worker-xai", "db-init"]:
        assert "ports" not in services.get(svc_name, {}), \
            f"Service '{svc_name}' in docker-compose.yml MUST NOT have host ports exposed (Task 7.5 isolation)"

    # Verify Caddy IS exposed on 80/443
    caddy_svc = services.get("caddy", {})
    assert "ports" in caddy_svc, "Caddy must expose HTTP/HTTPS ports to host"
    caddy_ports = str(caddy_svc["ports"])
    assert "80" in caddy_ports and "443" in caddy_ports

    # Verify monitoring services unexposed
    monitoring_compose_path = os.path.join(PROJECT_ROOT, "docker-compose.monitoring.yml")
    with open(monitoring_compose_path, "r", encoding="utf-8") as f:
        mon_compose = yaml.safe_load(f)

    mon_services = mon_compose.get("services", {})
    for svc_name in ["prometheus", "redis-exporter", "loki", "promtail", "flower"]:
        assert "ports" not in mon_services.get(svc_name, {}), \
            f"Monitoring service '{svc_name}' MUST NOT have host ports exposed (Task 7.5 isolation)"

    # Verify Grafana IS exposed on 3001
    grafana_svc = mon_services.get("grafana", {})
    assert "ports" in grafana_svc, "Grafana must expose dashboard port to host"
    assert "3001" in str(grafana_svc["ports"]) or "${GRAFANA_PORT:-3001}" in str(grafana_svc["ports"])


def test_7_6_compose_file_split_and_merging():
    """
    Verify split docker-compose files (`docker-compose.yml`, `docker-compose.monitoring.yml`,
    `docker-compose.security.yml`) are well-formed YAML and cleanly partition responsibilities (Task 7.6).
    """
    compose_files = [
        "docker-compose.yml",
        "docker-compose.monitoring.yml",
        "docker-compose.security.yml"
    ]
    for filename in compose_files:
        filepath = os.path.join(PROJECT_ROOT, filename)
        assert os.path.exists(filepath), f"Compose file {filename} must exist"
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert "services" in data, f"{filename} must define services block"


def test_7_10_production_environment_validation_and_secrets():
    """
    Verify `Settings.validate_production_environment()` fails fast with meaningful RuntimeError when
    insecure defaults (e.g. POSTGRES_PASSWORD or wildcard CORS) are detected in production mode (Task 10).
    """
    # 1. Test weak database password in production connecting to external host
    s_db = Settings(
        ENV="production",
        JWT_SECRET_KEY="a-very-secure-cryptographic-random-jwt-secret-key-32-chars+",
        POSTGRES_HOST="db.production.internal",
        POSTGRES_PASSWORD="abs_secret_change_me"
    )
    with pytest.raises(RuntimeError, match="FATAL SECURITY MISCONFIGURATION: POSTGRES_PASSWORD cannot use default or weak password"):
        s_db.validate_production_environment()

    # 2. Test wildcard CORS in production
    s_cors = Settings(
        ENV="production",
        JWT_SECRET_KEY="a-very-secure-cryptographic-random-jwt-secret-key-32-chars+",
        POSTGRES_HOST="db.production.internal",
        POSTGRES_PASSWORD="SuperStrongDatabasePassword123!@#$",
        CORS_ORIGINS=["*"]
    )
    with pytest.raises(RuntimeError, match=r"FATAL SECURITY MISCONFIGURATION: CORS_ORIGINS cannot allow wildcard '\*'"):
        s_cors.validate_production_environment()

    # 3. Test clean production configuration succeeds
    s_clean = Settings(
        ENV="production",
        JWT_SECRET_KEY="a-very-secure-cryptographic-random-jwt-secret-key-32-chars+",
        POSTGRES_HOST="db.production.internal",
        POSTGRES_PASSWORD="SuperStrongDatabasePassword123!@#$",
        CORS_ORIGINS=["https://app.agent-bastion.com"]
    )
    s_clean.validate_production_environment()  # Should not raise any exception
