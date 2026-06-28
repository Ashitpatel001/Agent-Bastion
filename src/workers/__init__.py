"""
ABSs v2.0 — Background Workers Package.

Provides Celery-based async task execution for:
  - XAI explanation generation (offloaded from the agent hot path).
  - Agent job execution (triggered by the /v1/agent/run API endpoint).

Requires a running Redis instance as the Celery message broker.
Configure via CELERY_BROKER_URL and CELERY_RESULT_BACKEND in .env.
"""

from workers.celery_app import celery_app  # noqa: F401

__all__ = ["celery_app"]
