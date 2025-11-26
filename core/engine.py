"""Database Engine Configuration."""

__all__ = [
    "SQLDB_ENGINE",
    "get_db_session",
    "SessionLocal",
]

import typing
import sqlmodel
from core.settings import get_settings


def get_engine():
    """Get database engine, creating lazily."""
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return sqlmodel.create_engine(
        url=settings.database_url,
        pool_pre_ping=True,
    )


# Lazy engine initialization
SQLDB_ENGINE = None


def _get_engine():
    global SQLDB_ENGINE
    if SQLDB_ENGINE is None:
        SQLDB_ENGINE = get_engine()
    return SQLDB_ENGINE


def SessionLocal() -> sqlmodel.Session:
    """Create a new database session."""
    return sqlmodel.Session(_get_engine())


def get_db_session() -> typing.Generator[sqlmodel.Session, None, None]:
    """FastAPI dependency to get a database session."""
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
