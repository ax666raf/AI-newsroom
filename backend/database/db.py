"""
db.py — Database connection, session management, and pgvector initialization.
"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.config import DATABASE_URL
from backend.database.models import Base

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,         # auto-reconnect on stale connections
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """
    Create all tables and enable the pgvector extension.

    Safe to call multiple times — CREATE EXTENSION IF NOT EXISTS
    and create_all are both idempotent.
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("pgvector extension enabled")

    Base.metadata.create_all(engine)
    logger.info("All tables created / verified")


@contextmanager
def get_db_session() -> Session:
    """
    Context manager that yields a SQLAlchemy session and handles
    commit / rollback / close automatically.

    Usage:
        with get_db_session() as session:
            session.add(obj)
            session.commit()
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI dependency that yields a DB session (for route injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
