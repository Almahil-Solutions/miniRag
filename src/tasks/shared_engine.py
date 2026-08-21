"""Shared database engine and sessionmaker singleton for Celery tasks.

Maintains a single process-level AsyncEngine and sessionmaker across task
executions to prevent database connection exhaustion and overhead of creating/disposing
engines per task run.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from helpers.config import get_settings
import logging

logger = logging.getLogger("celery.task")

_shared_engine: Optional[AsyncEngine] = None
_shared_sessionmaker: Optional[sessionmaker] = None


def get_shared_engine() -> AsyncEngine:
    """Get or create the singleton AsyncEngine for the current worker process."""
    global _shared_engine
    if _shared_engine is None:
        settings = get_settings()
        postgres_conn = (
            f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
        )
        _shared_engine = create_async_engine(
            postgres_conn,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        logger.info("Initialized shared Celery AsyncEngine singleton.")
    return _shared_engine


def get_shared_sessionmaker() -> sessionmaker:
    """Get or create the singleton sessionmaker for the current worker process."""
    global _shared_sessionmaker
    if _shared_sessionmaker is None:
        engine = get_shared_engine()
        _shared_sessionmaker = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
    return _shared_sessionmaker


async def dispose_shared_engine() -> None:
    """Dispose of the shared AsyncEngine during worker shutdown or cleanup."""
    global _shared_engine, _shared_sessionmaker
    if _shared_engine is not None:
        await _shared_engine.dispose()
        _shared_engine = None
        _shared_sessionmaker = None
        logger.info("Disposed shared Celery AsyncEngine.")
