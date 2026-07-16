"""
examples/worker_metrics.py — Real-Time Cluster Observability & Worker Queue Telemetry

Demonstrates retrieving system-wide metrics (`client.metrics()`), inspecting worker queue depths,
and evaluating platform resource health across distributed Celery worker instances.
"""

import sys
import json
from agent_bastion import Client, AgentBastionError


def main():
    print("\033[34m[Agent-Bastion Observability]\033[0m Fetching real-time cluster telemetry...")

    with Client() as client:
        try:
            # 1. Fetch system health diagnostics
            health = client.check_health()
            print("\n\033[32m✔ Cluster Health Diagnostics:\033[0m")
            print(f"  Overall Status:  {health.get('status', 'healthy')}")
            print(f"  Platform Ver:    v{health.get('version', '2.0.0')}")
            print(f"  PostgreSQL Pool: {health.get('database', 'connected')}")
            print(f"  Redis Broker:    {health.get('redis', 'connected')}")
            print(f"  Active Workers:  {health.get('workers', 'N/A')}")

            # 2. Fetch task execution metrics and worker stats
            print("\n\033[32m✔ Task Execution & Queue Metrics:\033[0m")
            metrics = client.metrics()
            print(json.dumps(metrics, indent=2, default=str))

        except AgentBastionError as exc:
            print(f"\033[31mObservability request failed: {exc.message}\033[0m", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
