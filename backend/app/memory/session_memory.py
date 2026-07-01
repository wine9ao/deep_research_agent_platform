"""Session Memory — stores and retrieves current task context."""

from __future__ import annotations

from typing import Any


class SessionMemory:
    """In-memory session context for the current research task.

    Stores intermediate results, key facts, and runtime context
    that agents need to share during execution.

    This is distinct from the ResearchState — it captures working
    memory that doesn't need to be persisted in the formal state.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self._history: list[dict] = []

    def set(self, key: str, value: Any) -> None:
        """Store a value in session memory."""
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from session memory."""
        return self._store.get(key, default)

    def add_context(self, agent: str, content: str, metadata: dict | None = None) -> None:
        """Add a context entry from an agent.

        Args:
            agent: Agent name.
            content: Key information or decision.
            metadata: Optional additional data.
        """
        from datetime import datetime
        self._history.append({
            "agent": agent,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })

    def get_context_for_agent(self, agent: str, limit: int = 5) -> list[dict]:
        """Get recent context entries relevant to an agent.

        Args:
            agent: Agent name to get context for.
            limit: Max number of entries.

        Returns:
            List of context entries.
        """
        # Return most recent entries (can be enhanced with relevance scoring)
        return self._history[-limit:]

    def get_all_context(self) -> list[dict]:
        """Get all context entries."""
        return self._history

    def clear(self) -> None:
        """Clear all session memory."""
        self._store.clear()
        self._history.clear()

    def summarize(self) -> str:
        """Generate a text summary of the session memory."""
        if not self._history:
            return "No session context available."

        lines = ["会话记忆摘要："]
        for entry in self._history[-10:]:
            lines.append(f"[{entry['agent']}] {entry['content'][:120]}")
        return "\n".join(lines)
