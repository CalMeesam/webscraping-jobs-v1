"""Database connection and session manager using SQLite and SQLAlchemy."""

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


def get_db_path() -> Path:
    """Get the active database file path."""
    return DEFAULT_DB_PATH


def get_engine(db_path: Path | str | None = None):
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None or db_path is not None:
        target_path = Path(db_path) if db_path else get_db_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{target_path.as_posix()}"
        _engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return _engine


def get_session_factory(db_path: Path | str | None = None):
    """Get or create the SQLAlchemy session factory."""
    global _SessionFactory
    engine = get_engine(db_path)
    if _SessionFactory is None or db_path is not None:
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
