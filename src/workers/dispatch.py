import socket
import logging
import os
import threading
from typing import Optional, Any

logger = logging.getLogger("workers.dispatch")

def is_redis_available() -> bool:
    """Check if the configured Redis broker is reachable."""
    from api.config import settings
    broker_url = settings.CELERY_BROKER_URL
    host = "localhost"
    port = 6379
    if "://" in broker_url:
        parts = broker_url.split("://")[1].split("/")[0].split(":")
        host = parts[0]
        if len(parts) > 1:
            try:
                port = int(parts[1])
            except ValueError:
                pass
    try:
        with socket.create_connection((host, port), timeout=0.05):
            return True
    except OSError:
        return False

def dispatch_task(celery_task, *args, queue: Optional[str] = None, priority: Optional[int] = None, **kwargs):
    """
    Dispatches a Celery task if Redis is available and running with multi-queue routing.
    Otherwise runs it asynchronously in a background daemon thread with a synthetic task ID.
    """
    if is_redis_available():
        try:
            apply_kwargs = {}
            if queue:
                apply_kwargs["queue"] = queue
            if priority is not None:
                apply_kwargs["priority"] = priority
            if apply_kwargs:
                return celery_task.apply_async(args=args, kwargs=kwargs, **apply_kwargs)
            return celery_task.delay(*args, **kwargs)
        except Exception as e:
            logger.warning("Celery dispatch failed (%s), falling back to background thread.", e)
    
    import uuid
    synthetic_id = f"local-task-{uuid.uuid4().hex[:12]}"
    logger.info("Executing task %s [%s] in local background thread (Redis not detected or offline)", getattr(celery_task, "__name__", str(celery_task)), synthetic_id)
    
    def _worker():
        try:
            # Celery tasks are callable and handle bound 'self' automatically
            celery_task(*args, **kwargs)
        except Exception as e:
            logger.exception("Error executing background task %s: %s", getattr(celery_task, "__name__", str(celery_task)), e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    
    class SyntheticTaskResult:
        def __init__(self, task_id: str, thread: threading.Thread):
            self.id = task_id
            self.thread = thread
            self.status = "QUEUED"
            
    return SyntheticTaskResult(synthetic_id, t)
