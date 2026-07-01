"""Checkpoint manager — persists ResearchState in SQLite.

Usage::

    from app.state.research_state import ResearchState
    from app.state.checkpoint import CheckpointManager

    mgr = CheckpointManager("checkpoints.db")
    await mgr.save(state)
    loaded = await mgr.load(state.task_id)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.state.research_state import ResearchState


class CheckpointManager:
    """SQLite-backed checkpoint store for ResearchState.

    Uses sync sqlite3 (standard library) wrapped for async usage.
    The operations are fast enough (<1ms) that sync is fine.

    Parameters
    ----------
    db_path : str | Path
        Filesystem path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path = "data/checkpoints.db") -> None:
        self.db_path: Path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Create the checkpoints table if it does not exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    task_id    TEXT PRIMARY KEY,
                    state_json TEXT    NOT NULL,
                    created_at TEXT    NOT NULL,
                    updated_at TEXT    NOT NULL
                )
                """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def save(self, state: ResearchState) -> None:
        """Persist state (insert or replace) into the checkpoints table."""
        state.update_timestamp()
        self._ensure_table()

        state_json = json.dumps(state.to_dict(), ensure_ascii=False)
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO checkpoints (task_id, state_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (state.task_id, state_json, now, now),
            )
            conn.commit()

    async def load(self, task_id: str) -> Optional[ResearchState]:
        """Load and reconstruct a ResearchState by task_id.

        Returns None when no row matches.
        """
        self._ensure_table()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT state_json FROM checkpoints WHERE task_id = ?",
                (task_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        data = json.loads(row["state_json"])
        return ResearchState.from_dict(data)

    async def list_all(self) -> list[dict[str, str]]:
        """Return summary rows for every stored checkpoint."""
        self._ensure_table()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT task_id, created_at, updated_at FROM checkpoints "
                "ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    async def cleanup(self, days: int) -> int:
        """Delete checkpoints older than *days* days. Returns deleted count."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM checkpoints WHERE updated_at < ?",
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount
