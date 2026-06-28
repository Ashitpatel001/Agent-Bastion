import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db, close_db
from api.routes import tenants, agents, security, policies

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
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

# CORS Middleware for Dashboard/Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Include routers
app.include_router(tenants.router)
app.include_router(agents.router)
app.include_router(security.router)
app.include_router(policies.router)

# Mount static files for HTML/CSS/JS frontend
app.mount("/static", StaticFiles(directory="src/api/static"), name="static")

@app.get("/")
async def read_index():
    """Serve the landing page and developer console."""
    return FileResponse("src/api/static/index.html")

@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "abs-proxy-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
