"""Database connection and session manager supporting PostgreSQL and SQLite via SQLAlchemy."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "extraction_history.db"


class Base(DeclarativeBase):
    """Base ORM class."""
    pass


_engine = None
_SessionFactory = None


def get_db_url(db_path: Path | str | None = None) -> str:
    """Resolve database URL string from explicit argument or environment configuration."""
    if db_path is not None:
        db_path_str = str(db_path)
        if db_path_str.startswith("postgresql://") or db_path_str.startswith("postgres://"):
            return db_path_str
        target_path = Path(db_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{target_path.as_posix()}"

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Handle Heroku/legacy postgres:// scheme
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql://", 1)
        return env_url

    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"


def reset_engine_cache() -> None:
    """Reset cached engine and session factory (useful for testing)."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionFactory = None


def get_engine(db_path: Path | str | None = None):
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None or db_path is not None:
        db_url = get_db_url(db_path)
        
        is_sqlite = db_url.startswith("sqlite")
        connect_args = {"check_same_thread": False} if is_sqlite else {}
        
        engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            echo=False,
        )
        if db_path is None:
            _engine = engine
            return _engine
        return engine

    return _engine


def get_session_factory(db_path: Path | str | None = None):
    """Get or create the SQLAlchemy session factory."""
    global _SessionFactory
    engine = get_engine(db_path)
    if _SessionFactory is None or db_path is not None:
        factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        if db_path is None:
            _SessionFactory = factory
            return _SessionFactory
        return factory

    return _SessionFactory


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize database schema, creating tables if they don't exist."""
    engine = get_engine(db_path)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session(db_path: Path | str | None = None) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session_factory = get_session_factory(db_path)
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

