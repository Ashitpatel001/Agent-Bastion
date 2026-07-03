import socket
import logging
import os
import threading

logger = logging.getLogger("workers.dispatch")

def is_redis_available() -> bool:
    """Check if the configured Redis broker is reachable."""
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
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

def dispatch_task(celery_task, *args, **kwargs):
    """
    Dispatches a Celery task if Redis is available.
    Otherwise runs it asynchronously in a background daemon thread.
    """
    if is_redis_available():
        try:
            return celery_task.delay(*args, **kwargs)
        except Exception as e:
            logger.warning("Celery dispatch failed (%s), falling back to background thread.", e)
    
    logger.info("Executing task %s in local background thread (Redis not detected)", getattr(celery_task, "__name__", str(celery_task)))
    
    def _worker():
        try:
            # Celery tasks are callable and handle bound 'self' automatically
            celery_task(*args, **kwargs)
        except Exception as e:
            logger.exception("Error executing background task %s: %s", getattr(celery_task, "__name__", str(celery_task)), e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t
