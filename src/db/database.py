import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

load_dotenv()

logger = logging.getLogger("db.database")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Build DATABASE_URL from individual POSTGRES_* env vars (handles special
# characters in passwords via URL encoding) OR use an explicit DATABASE_URL.
_explicit_url = os.getenv("DATABASE_URL")

if _explicit_url:
    DATABASE_URL: str = _explicit_url
else:
    _pg_user = os.getenv("POSTGRES_USER")
    _pg_pass = os.getenv("POSTGRES_PASSWORD")
    _pg_host = os.getenv("POSTGRES_HOST", "localhost")
    _pg_port = os.getenv("POSTGRES_PORT", "5432")
    _pg_db   = os.getenv("POSTGRES_DB")

    if _pg_user and _pg_pass and _pg_db:
        # URL-encode password to safely handle @, :, /, etc.
        DATABASE_URL = (
            f"postgresql+asyncpg://{quote_plus(_pg_user)}:{quote_plus(_pg_pass)}"
            f"@{_pg_host}:{_pg_port}/{_pg_db}"
        )
    else:
        # Default: aiosqlite for local dev (free, zero-config).
        DATABASE_URL = "sqlite+aiosqlite:///./abs_security.db"

# SQLite requires special pooling to allow concurrent async access.
_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": os.getenv("DB_ECHO", "false").lower() == "true",
    "future": True,
}

if _is_sqlite:
    # StaticPool keeps a single connection alive across threads for SQLite,
    # preventing "database is locked" errors in async contexts.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool
else:
    # PostgreSQL: use a connection pool.
    _engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    _engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    _engine_kwargs["pool_pre_ping"] = True  # Verify connections before use.

# ---------------------------------------------------------------------------
# Engine & Session Factory
# ---------------------------------------------------------------------------
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-load issues after commit.
)


# ---------------------------------------------------------------------------
# Dependency — FastAPI-compatible async session generator
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async database session.

    Usage with FastAPI:
        @app.get("/")
        async def root(db: AsyncSession = Depends(get_db)):
            ...

    Usage standalone:
        async with get_db_context() as db:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for use outside of FastAPI (e.g., Celery workers,
    CLI scripts, tests).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """
    Optionally create all tables at application startup.

    By default this is a **no-op** in production. Schema creation is handled
    by the one-shot ``init_db.py`` script (or Alembic migrations) which runs
    *before* the API workers start, avoiding the race condition where
    multiple uvicorn workers simultaneously attempt to ``CREATE TYPE`` and
    hit ``pg_type_typname_nsp_index`` unique-constraint violations.

    Set the environment variable ``AUTO_CREATE_TABLES=true`` to restore the
    old behaviour (useful for local dev with SQLite where there is only one
    worker and no ENUM-type conflict).
    """
    auto_create = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"

    if auto_create:
        from db.models import Base  # Local import to avoid circular dependency.

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized (engine: %s)", DATABASE_URL.split("://")[0])
    else:
        logger.info(
            "Skipping auto table creation (set AUTO_CREATE_TABLES=true to enable). "
            "Run 'python init_db.py' to initialize the schema."
        )


async def close_db() -> None:
    """Dispose of the engine's connection pool. Call on shutdown."""
    await engine.dispose()
    logger.info("Database connection pool disposed.")
