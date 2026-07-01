"""Database manager for SQLite with sync support (no async dependencies required)."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..utils.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class DatabaseManager:
    """Manages database connections and sessions.

    Uses sync SQLAlchemy with SQLite by default.
    No aiosqlite dependency required.
    """

    def __init__(self, database_url: str | None = None) -> None:
        settings = get_settings()
        self.database_url = database_url or settings.DATABASE_URL

        # Ensure SQLite path exists
        if "sqlite" in self.database_url:
            db_path = self.database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.isabs(db_path):
                os.makedirs(db_dir, exist_ok=True)

        self.engine = create_engine(self.database_url, echo=False)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_all_sync(self) -> None:
        """Create all tables."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a sync database session."""
        return self.session_factory()

    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()


# ── Global instance ───────────────────────────────────────────────────────

_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
