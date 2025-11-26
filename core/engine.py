"""Database Engine Configuration."""

__all__ = [
    "SQLDB_ENGINE",
    "get_db_session",
    "SessionLocal",
]

import typing
import sqlmodel
from core.settings import get_settings


settings = get_settings()

SQLDB_ENGINE = sqlmodel.create_engine(
    url=settings.database_url,
    pool_pre_ping=True,
)


def SessionLocal() -> sqlmodel.Session:
    """Create a new database session."""
    return sqlmodel.Session(SQLDB_ENGINE)


def get_db_session() -> typing.Generator[sqlmodel.Session, None, None]:
    """FastAPI dependency to get a database session."""
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
