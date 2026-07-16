"""
workers/celery_app.py — Celery Application Factory.

Centralised Celery instance shared by all worker modules.
Configured for reliability:
  - Late acks: tasks are acknowledged AFTER completion, not on receipt.
  - Reject on worker lost: tasks requeue if a worker crashes mid-execution.
  - Serialisation: JSON for broad compatibility and debuggability.
  - Soft/hard time limits: prevent runaway tasks from monopolising workers.

Broker: Redis (matches the free-tier infrastructure plan).

Usage:
    # Start the worker (from project root):
    celery -A workers.celery_app worker --loglevel=info --concurrency=2

    # Start with specific queues:
    celery -A workers.celery_app worker -Q xai,agents,default --loglevel=info

    # Monitor with Flower (optional):
    celery -A workers.celery_app flower --port=5555
"""

import os
import logging

from celery import Celery
from dotenv import load_dotenv

from api.config import settings

logger = logging.getLogger("workers.celery_app")


# Configuration from central settings
BROKER_URL: str = settings.CELERY_BROKER_URL
RESULT_BACKEND: str = settings.CELERY_RESULT_BACKEND


# Celery instance
celery_app = Celery(
    "abs_workers",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)


# Configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability & Resource Protection (Task 4.3 & 4.5)
    task_acks_late=True,              
    task_reject_on_worker_lost=True,    # Requeue if worker crashes
    worker_prefetch_multiplier=1,       

    # Time limits (Task 4.5)
    task_soft_time_limit=300,           # 5 min soft time limit
    task_time_limit=360,                # 6 min hard kill time limit

    # Result expiry 
    result_expires=3600,                

    # Task priority & routing (Stage A - Queue Architecture)
    task_queue_max_priority=10,
    task_default_priority=5,
    task_routes={
        "workers.xai_tasks.*": {"queue": "xai"},
        "workers.agent_tasks.run_agent_task": {"queue": "agents"},
        "workers.agent_tasks.cancel_agent_task": {"queue": "agents"},
    },

    # Default queue 
    task_default_queue="default",

    # Timezone 
    timezone="UTC",
    enable_utc=True,

    # Logging
    worker_hijack_root_logger=False,  
)


# Auto-discover task modules
celery_app.autodiscover_tasks(["workers"])

logger.info(
    "Celery app configured (broker=%s, backend=%s)",
    BROKER_URL.split("@")[-1] if "@" in BROKER_URL else BROKER_URL,
    RESULT_BACKEND.split("@")[-1] if "@" in RESULT_BACKEND else RESULT_BACKEND,
)
