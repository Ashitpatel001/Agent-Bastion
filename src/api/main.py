import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import os

from db.database import init_db, close_db
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
    logger.info("Starting ABSs API Gateway...")
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
    
    # Update context with response data
    ctx["status_code"] = response.status_code
    ctx["execution_time_ms"] = round(execution_time, 2)
    request_context.set(ctx)
    
    # Only log path if not health
    if request.url.path not in ["/health", "/live", "/ready"]:
        logger.info(f"{request.method} {request.url.path} completed")
        
    response.headers["x-request-id"] = req_id
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

# Phase 12: Custom Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error_code": "INTERNAL_ERROR"},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "error_code": "VALIDATION_ERROR"},
    )

# CORS Middleware for Dashboard/Frontend (Phase 13 Hardened)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000").split(",")
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
    """Simple health check endpoint."""
    return {"status": "ok", "service": "abs-proxy-api"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
    
