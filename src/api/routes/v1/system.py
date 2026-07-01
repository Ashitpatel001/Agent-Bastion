import logging
import time
from datetime import datetime, timezone
from fastapi import APIRouter

logger = logging.getLogger("api.routes.v1.system")
router = APIRouter()

_start_time = time.time()


@router.get("/health")
async def system_health():
    """Comprehensive system health check with DB and Redis connectivity."""
    health = {
        "status": "ok",
        "service": "abs-proxy-api",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "components": {}
    }

    # Check database
    try:
        from db.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Redis
    try:
        import redis
        import os
        r = redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        r.ping()
        health["components"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    health["database"] = health["components"].get("database", {}).get("status", "unknown")
    health["redis"] = health["components"].get("redis", {}).get("status", "unknown")
    health["timestamp"] = datetime.now(timezone.utc).isoformat()

    return health

