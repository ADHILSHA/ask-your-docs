# app/db.py
"""Database engine, session, and the declarative base.

One SQLAlchemy setup for both SQLite (local dev) and Postgres (Render), chosen
by DATABASE_URL. Routes get a session via the `get_db` dependency; models
inherit from `Base`. Schema is managed by Alembic migrations
(`alembic upgrade head`), not create_all.
"""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

# SQLite needs check_same_thread=False because FastAPI runs sync routes in a
# threadpool; Postgres ignores it. pool_pre_ping avoids stale connections.
_connect_args = (
    {"check_same_thread": False}
    if _settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Declarative base all ORM models inherit from."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
