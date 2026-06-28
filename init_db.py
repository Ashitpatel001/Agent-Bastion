"""
init_db.py — One-shot database schema initializer for ABSs v2.0.

Run this ONCE before starting the API to create all tables and ENUM types.
This avoids the race condition where multiple uvicorn workers simultaneously
attempt to CREATE TYPE, causing:

    duplicate key value violates unique constraint "pg_type_typname_nsp_index"

Usage:
    python init_db.py          # Create tables (idempotent via checkfirst=True)
    python init_db.py --drop   # Drop and recreate all tables (DESTRUCTIVE)

In Docker Compose, this runs as a one-shot init container that exits after
schema creation, before the API and worker services start.
"""

import asyncio
import logging
import os
import sys

# Ensure the src directory is on the path (matches the PYTHONPATH=/app layout).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from db.database import engine, DATABASE_URL
from db.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("init_db")


async def create_schema(drop_first: bool = False) -> None:
    """Create all database tables and ENUM types.

    Args:
        drop_first: If True, drop all tables before recreating them.
                    **Destructive** — only use in dev/test environments.
    """
    db_backend = DATABASE_URL.split("://")[0]
    logger.info("Connecting to database (engine: %s)...", db_backend)

    async with engine.begin() as conn:
        if drop_first:
            logger.warning("Dropping all existing tables!")
            await conn.run_sync(Base.metadata.drop_all)

        logger.info("Creating tables and ENUM types (checkfirst=True)...")
        await conn.run_sync(Base.metadata.create_all)

    # Dispose the engine so the script doesn't hold connections open.
    await engine.dispose()
    logger.info("✅ Database schema initialized successfully.")


def main() -> None:
    drop = "--drop" in sys.argv
    if drop:
        logger.warning("⚠️  --drop flag detected. ALL DATA WILL BE LOST.")

    asyncio.run(create_schema(drop_first=drop))


if __name__ == "__main__":
    main()
