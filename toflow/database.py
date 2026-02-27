"""Database connection and session management."""

from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = Path.home() / ".toflow" / "toflow.db"

_db_initialized = False
_engine = None
_session_factory = None


class Base(DeclarativeBase):
    pass


def get_engine():
    """Return SQLAlchemy engine. Cached after first call."""
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}")
    return _engine


def get_session():
    """Create a new database session."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine())
    return _session_factory()


def init_db():
    """Initialize database and create all tables. Runs at most once per application lifecycle."""
    global _db_initialized
    if _db_initialized:
        return
    from toflow.models import NowTodayItem, Project, Session, Track, TodoItem

    engine = get_engine()
    Base.metadata.create_all(engine)
    _db_initialized = True


@contextmanager
def db_session():
    """Context manager for database session lifecycle (auto commit/rollback)."""
    init_db()
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
