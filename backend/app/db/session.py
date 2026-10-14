"""Database session and engine management using SQLAlchemy 2.x."""

from __future__ import annotations

import logging
from collections.abc import Generator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings

logger = logging.getLogger(__name__)


def normalize_database_url(url: str | None) -> str:
    """Normalize database connection URL to ensure psycopg 3 compatibility."""
    if not url or not url.strip():
        # Development fallback when PostgreSQL is not configured locally
        return "sqlite:///./health_copilot.db"

    clean_url = url.strip()
    # Normalize standard postgresql:// to postgresql+psycopg:// for psycopg v3
    if clean_url.startswith("postgresql://"):
        return clean_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if clean_url.startswith("postgres://"):
        return clean_url.replace("postgres://", "postgresql+psycopg://", 1)
    return clean_url


@lru_cache(maxsize=4)
def get_engine(database_url: str | None = None) -> Engine:
    """Create or return cached SQLAlchemy engine."""
    settings = get_settings()
    url = normalize_database_url(database_url or settings.database_url)

    engine_kwargs: dict[str, Any] = {
        "future": True,
        "pool_pre_ping": True,
    }

    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL pool configuration
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    logger.info("Initializing database engine (driver: %s)", url.split("://")[0])
    return create_engine(url, **engine_kwargs)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Build a sessionmaker bound to the given or default engine."""
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session for a single request."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
