"""Database connection management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import logging

from src.config import get_config

logger = logging.getLogger(__name__)


def get_engine():
    """Create and return SQLAlchemy engine."""
    config = get_config()  # FIX: call inside function so lru_cache is respected

    engine = create_engine(
        config.database_url,
        echo=config.debug,
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Enable TimescaleDB extension when connecting."""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
            dbapi_conn.commit()
            logger.debug("TimescaleDB extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable TimescaleDB extension: {e}")
        finally:
            cursor.close()

    return engine


# Session factory — built lazily so get_engine() uses the cached config
def _make_session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


SessionLocal = _make_session_factory()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session with automatic commit/rollback.

    Usage:
        with get_db_session() as session:
            session.add(some_object)
            # commits automatically on exit, rolls back on exception

    Yields:
        Session: SQLAlchemy session

    Raises:
        Exception: Re-raises any exception after rolling back
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Transaction rolled back due to error: {e}")
        raise
    finally:
        session.close()
        logger.debug("Session closed")


# FIX: removed the broken get_session() which used `yield` but declared return type
# as `Session` (not a Generator), making it silently return a generator object to
# callers expecting a real session. Use get_db_session() with a `with` statement instead.


def init_db() -> None:
    """Create all tables. Safe to call multiple times (uses CREATE IF NOT EXISTS)."""
    from src.database.schema import Base

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully!")
    print("Database initialized successfully!")


def drop_db() -> None:
    """Drop all tables. Irreversible — use only in dev/test."""
    from src.database.schema import Base

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped!")
    print("Database dropped successfully!")
