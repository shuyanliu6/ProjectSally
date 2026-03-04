"""Database connection management with improved session handling."""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from src.config import get_config
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

config = get_config()


def get_engine():
    """Create and return SQLAlchemy engine."""
    engine = create_engine(
        config.database_url,
        echo=config.debug,
        poolclass=NullPool,  # Disable connection pooling for simplicity
    )

    # Enable TimescaleDB extension on connection
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


# Create session factory
SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def get_db_session() -> Session:
    """
    Get database session with automatic commit/rollback.
    
    Usage:
        with get_db_session() as session:
            asset = Asset(symbol="AAPL", name="Apple")
            session.add(asset)
            # Automatically commits and closes
    
    Yields:
        Session: SQLAlchemy session object
        
    Raises:
        Exception: Any exception raised during session usage
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


def get_session() -> Session:
    """
    Legacy method for backward compatibility.
    Use get_db_session() context manager instead.
    
    Deprecated: Use get_db_session() with 'with' statement
    """
    logger.warning("get_session() is deprecated, use get_db_session() instead")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Initialize database with all tables."""
    from src.database.schema import Base

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully!")
    print("Database initialized successfully!")


def drop_db():
    """Drop all tables (use with caution!)."""
    from src.database.schema import Base

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    logger.warning("Database dropped successfully!")
    print("Database dropped successfully!")