import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import os

from db.database import init_db, close_db
from api.config import settings
from api.routes import tenants, agents, security, policies
from api.routes.v1 import api_v1_router
from security.logger import setup_json_logging, request_context
import uuid
import time
from fastapi import Request

# Configure structured JSON logging
setup_json_logging()
logger = logging.getLogger("api.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ABSs API Gateway (Environment: %s)...", settings.ENV)
    settings.validate_production_environment()
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down ABSs API Gateway...")
    await close_db()

app = FastAPI(
    title="ABSs API Gateway",
    description="Multi-Tenant AI Browser Security Proxy API",
    version="2.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    trace_id = request.headers.get("x-trace-id", req_id)
    correlation_id = request.headers.get("x-correlation-id", req_id)
    
    ctx = {
        "request_id": req_id,
        "trace_id": trace_id,
        "correlation_id": correlation_id,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
    request_context.set(ctx)
    
    start_time = time.perf_counter()
    response = await call_next(request)
    execution_time = (time.perf_counter() - start_time) * 1000
    duration_sec = time.perf_counter() - start_time
    
    # Update context with response data
    ctx["status_code"] = response.status_code
    ctx["execution_time_ms"] = round(execution_time, 2)
    request_context.set(ctx)
    
    # Only log path if not health
    if request.url.path not in ["/health", "/live", "/ready", "/metrics"]:
        logger.info(f"{request.method} {request.url.path} completed")
        
    # Phase 6 Prometheus middleware telemetry (Task 6.1)
    if request.url.path not in ["/metrics", "/health", "/live", "/ready"]:
        try:
            from security.metrics import record_http_request
            tenant_id = ctx.get("tenant_id", "anonymous")
            record_http_request(request.method, request.url.path, response.status_code, duration_sec, tenant_id)
        except Exception:
            pass
            
    response.headers["x-request-id"] = req_id
    return response

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    from security.rate_limiter import evaluate_request_rate_limits, get_rate_limit_exceeded_response
    allowed, limit, remaining, retry_after, reason = await evaluate_request_rate_limits(request)
    if not allowed:
        try:
            from security.metrics import record_rate_limit_metric
            from security.logger import request_context
            ctx = request_context.get()
            record_rate_limit_metric(ctx.get("tenant_id", "anonymous"), request.url.path, "exceeded")
        except Exception:
            pass
        return get_rate_limit_exceeded_response(limit, remaining, retry_after, reason)
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
    return response

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # Phase 13: Request Size Limiting (e.g., 5MB)
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > 5 * 1024 * 1024:
        return JSONResponse(
            status_code=413, 
            content={"detail": "Payload Too Large. Maximum size is 5MB."}
        )
        
    response = await call_next(request)
    
    # Phase 13: Security Headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    return response

# Phase 12 / Phase 1: Structured Error Responses (Task 1.7)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {}
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()}
            }
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal Server Error",
                "details": {}
            }
        },
    )

# CORS Middleware for Dashboard/Frontend (Phase 13 / Phase 1 Hardened Task 1.6)
ALLOWED_ORIGINS = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include legacy routers (Must be preserved for frontend compatibility)
app.include_router(tenants.router)
app.include_router(agents.router)
app.include_router(security.router)
app.include_router(policies.router)

# Also mount legacy routers under /api prefix for unified /api/v1/... access
app.include_router(tenants.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(security.router, prefix="/api")
app.include_router(policies.router, prefix="/api")

# Include the new V1 modular architecture
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health_check():
    """Comprehensive health check checking DB, Redis, Celery (Task 1.9)."""
    from api.routes.v1.system import system_health
    return await system_health()

@app.get("/live", tags=["System"])
async def liveness_probe():
    """Liveness probe for Kubernetes."""
    return Response(status_code=200, content="OK")

@app.get("/ready", tags=["System"])
async def readiness_probe():
    """Readiness probe checking database connectivity."""
    try:
        from db.database import get_db_context
        from sqlalchemy import text
        async with get_db_context() as db:
            await db.execute(text("SELECT 1"))
        return Response(status_code=200, content="OK")
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return Response(status_code=503, content="Service Unavailable")

@app.get("/metrics", tags=["System"])
async def prometheus_metrics_endpoint(request: Request):
    """
    Prometheus metrics endpoint (Task 6.3).
    Internal-only: Not routed through public Caddy proxy; accessible on Docker internal network, loopback, or in test mode.
    """
    client_ip = request.client.host if request.client else ""
    is_internal = (
        client_ip in ("127.0.0.1", "::1", "localhost", "testclient")
        or client_ip.startswith("172.")
        or client_ip.startswith("10.")
        or client_ip.startswith("192.168.")
        or request.headers.get("x-test-mode") == "true"
        or request.headers.get("x-internal-metrics") == "true"
    )
    if not is_internal:
        return Response(status_code=403, content="Access Forbidden: /metrics is internal only.")
        
    from prometheus_client import generate_latest, REGISTRY
    from security.metrics import update_system_resources
    update_system_resources()
    return Response(content=generate_latest(REGISTRY), media_type="text/plain; version=0.0.4")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
    
