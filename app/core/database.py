"""
Database engine, session factory, and base model for SQLAlchemy.
SQLite-specific PRAGMAs are applied on every connection.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings


# ── SQLite-specific: apply PRAGMAs on connect ──
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Configure SQLite for optimal performance and safety."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")       # Write-Ahead Logging
    cursor.execute("PRAGMA foreign_keys = ON")         # Enforce FK constraints
    cursor.execute("PRAGMA busy_timeout = 5000")       # Wait 5s on lock contention
    cursor.execute("PRAGMA synchronous = NORMAL")      # Balance safety/speed
    cursor.execute("PRAGMA cache_size = -64000")       # 64 MB page cache
    cursor.execute("PRAGMA temp_store = MEMORY")       # Temp tables in memory
    cursor.close()


# ── Engine ──
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + FastAPI
    echo=settings.DEBUG,  # Log SQL in debug mode
)

# Attach SQLite PRAGMAs if using SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    event.listen(engine, "connect", _set_sqlite_pragmas)

# ── Session Factory ──
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Base Model ──
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# ── Dependency: get DB session ──
def get_db():
    """
    FastAPI dependency that yields a database session.
    Automatically closes the session when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
