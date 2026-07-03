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

load_dotenv()

logger = logging.getLogger("workers.celery_app")


# Configuration from environment
BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


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

    # Reliability
    task_acks_late=True,              
    task_reject_on_worker_lost=True,    # Requeue if worker crashes
    worker_prefetch_multiplier=1,       

    # Time limits
    task_soft_time_limit=300,           
    task_time_limit=360,                

    # Result expiry 
    result_expires=3600,                

    # Task routing
    task_routes={
        "workers.xai_tasks.*": {"queue": "xai"},
        "workers.agent_tasks.*": {"queue": "agents"},
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
