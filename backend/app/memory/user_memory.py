"""User Memory — stores user preferences and research history."""

from __future__ import annotations

import json
from typing import Any

from ..db.database import get_db_manager
from ..db.models import UserMemory
from ..utils.logger import get_logger

logger = get_logger(__name__)


class UserMemoryManager:
    """Manages user preferences and historical research context.

    Stores:
    - User historical questions
    - Frequently used research types
    - Preferred report structures
    - Historical report summaries
    - User feedback

    Uses SQLite for storage with a simple key-value pattern.
    """

    def __init__(self, user_id: str = "default") -> None:
        self.user_id = user_id
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Ensure the database tables exist."""
        try:
            db = get_db_manager()
            db.create_all_sync()
        except Exception as e:
            logger.warning(f"Failed to ensure user_memory table: {e}")

    def save_preference(self, key: str, value: Any) -> None:
        """Save a user preference.

        Args:
            key: Preference key (e.g., 'preferred_research_type').
            value: Preference value (will be JSON serialized).
        """
        db = get_db_manager()
        with db.session_factory() as session:
            # Check if exists
            existing = session.query(UserMemory).filter_by(
                user_id=self.user_id, key=key, memory_type="preference"
            ).first()
            if existing:
                existing.value = json.dumps(value, ensure_ascii=False)
            else:
                memory = UserMemory(
                    user_id=self.user_id,
                    memory_type="preference",
                    key=key,
                    value=json.dumps(value, ensure_ascii=False),
                )
                session.add(memory)
            session.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference.

        Args:
            key: Preference key.
            default: Default value if not found.

        Returns:
            The stored preference value or default.
        """
        db = get_db_manager()
        with db.session_factory() as session:
            memory = session.query(UserMemory).filter_by(
                user_id=self.user_id, key=key, memory_type="preference"
            ).first()
            if memory:
                try:
                    return json.loads(memory.value)
                except (json.JSONDecodeError, TypeError):
                    return memory.value
            return default

    def save_research_history(self, query: str, research_type: str, summary: str) -> None:
        """Save a research task to history.

        Args:
            query: The research question.
            research_type: The research type.
            summary: Brief summary of results.
        """
        from datetime import datetime

        db = get_db_manager()
        with db.session_factory() as session:
            memory = UserMemory(
                user_id=self.user_id,
                memory_type="history",
                key=f"research_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                value=json.dumps({
                    "query": query,
                    "research_type": research_type,
                    "summary": summary,
                    "timestamp": datetime.now().isoformat(),
                }, ensure_ascii=False),
            )
            session.add(memory)
            session.commit()

    def get_research_history(self, limit: int = 10) -> list[dict]:
        """Get recent research history.

        Args:
            limit: Max number of history entries.

        Returns:
            List of historical research entries.
        """
        db = get_db_manager()
        with db.session_factory() as session:
            memories = (
                session.query(UserMemory)
                .filter_by(user_id=self.user_id, memory_type="history")
                .order_by(UserMemory.created_at.desc())
                .limit(limit)
                .all()
            )
            result = []
            for m in memories:
                try:
                    result.append(json.loads(m.value))
                except (json.JSONDecodeError, TypeError):
                    result.append({"raw": m.value})
            return result

    def save_feedback(self, task_id: str, feedback: str, rating: int = 0) -> None:
        """Save user feedback on a research report.

        Args:
            task_id: The research task ID.
            feedback: User feedback text.
            rating: User rating (1-5).
        """
        db = get_db_manager()
        with db.session_factory() as session:
            memory = UserMemory(
                user_id=self.user_id,
                memory_type="feedback",
                key=f"feedback_{task_id}",
                value=json.dumps({
                    "task_id": task_id,
                    "feedback": feedback,
                    "rating": rating,
                }, ensure_ascii=False),
            )
            session.add(memory)
            session.commit()

    def get_common_research_types(self) -> list[str]:
        """Get user's most frequently used research types.

        Returns:
            List of research types sorted by frequency.
        """
        history = self.get_research_history(50)
        type_counts: dict[str, int] = {}
        for entry in history:
            rt = entry.get("research_type", "综合研究")
            type_counts[rt] = type_counts.get(rt, 0) + 1
        return sorted(type_counts, key=type_counts.get, reverse=True)
