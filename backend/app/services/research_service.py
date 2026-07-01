"""Research Service — orchestrates research tasks."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from ..graph.research_graph import ResearchGraph
from ..state.research_state import ResearchState
from ..state.checkpoint import CheckpointManager
from ..db.database import get_db_manager
from ..db.models import ResearchTask
from ..tools.text2sql import Text2SQLTool
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ResearchService:
    """Manages research task lifecycle: creation, execution, status, results.

    Handles:
    - Creating new research tasks
    - Running the research pipeline asynchronously
    - Tracking progress and status
    - Storing and retrieving results
    """

    def __init__(self) -> None:
        self._checkpoint_manager = CheckpointManager()
        self._running_tasks: dict[str, ResearchState] = {}

    async def create_task(self, query: str, research_type: str = "", use_mock: bool = True) -> dict:
        """Create a new research task.

        Args:
            query: Research question.
            research_type: Optional research type hint.
            use_mock: Whether to use mock data sources.

        Returns:
            dict with task_id and status.
        """
        state = ResearchState(
            user_query=query,
            research_type=research_type or "",
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Save to database
        db = get_db_manager()
        db.create_all_sync()
        with db.session_factory() as session:
            task = ResearchTask(
                task_id=state.task_id,
                user_query=query,
                research_type=research_type or "综合研究",
                status="created",
                use_mock=use_mock,
            )
            session.add(task)
            session.commit()

        # Save checkpoint
        await self._checkpoint_manager.save(state)

        logger.info(f"[ResearchService] Created task {state.task_id[:8]}: {query[:60]}...")
        return {"task_id": state.task_id, "status": "created"}

    async def run_task(self, task_id: str) -> dict:
        """Start executing a research task.

        Args:
            task_id: The task UUID.

        Returns:
            dict with task_id and status.
        """
        # Load state from checkpoint
        state = await self._checkpoint_manager.load(task_id)
        if state is None:
            # Try loading from database
            state = self._load_state_from_db(task_id)
        if state is None:
            return {"task_id": task_id, "status": "error", "error": "Task not found"}

        # Update DB status
        self._update_task_status(task_id, "running", "init")

        # Run in background
        asyncio.create_task(self._execute_pipeline(state))

        logger.info(f"[ResearchService] Started task {task_id[:8]}")
        return {"task_id": task_id, "status": "running"}

    async def _execute_pipeline(self, state: ResearchState) -> None:
        """Execute the research pipeline in the background."""
        task_id = state.task_id
        self._running_tasks[task_id] = state

        try:
            def progress_cb(step: str, details: dict) -> None:
                self._update_task_status(task_id, "running", step)

            graph = ResearchGraph(
                max_iterations=state.max_iterations,
                checkpoint_manager=self._checkpoint_manager,
                progress_callback=progress_cb,
            )
            final_state = await graph.run(state)

            # Save final results to DB
            self._save_final_results(final_state)

        except Exception as e:
            logger.error(f"[ResearchService] Task {task_id[:8]} failed: {e}", exc_info=True)
            self._update_task_status(task_id, "error", "error", error=str(e))
        finally:
            self._running_tasks.pop(task_id, None)

    async def get_status(self, task_id: str) -> dict:
        """Get current task status.

        Args:
            task_id: The task UUID.

        Returns:
            dict with task status info.
        """
        # Check running tasks first
        if task_id in self._running_tasks:
            state = self._running_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "running",
                "current_step": state.current_step,
                "progress": self._estimate_progress(state.current_step),
                "iteration_count": state.iteration_count,
            }

        # Check database
        db = get_db_manager()
        with db.session_factory() as session:
            task = session.query(ResearchTask).filter_by(task_id=task_id).first()
            if task:
                return {
                    "task_id": task_id,
                    "status": task.status,
                    "current_step": task.current_step,
                    "progress": task.progress,
                    "iteration_count": task.iteration_count,
                }

        return {"task_id": task_id, "status": "not_found"}

    async def get_result(self, task_id: str) -> dict:
        """Get final research results.

        Args:
            task_id: The task UUID.

        Returns:
            dict with final report, charts, sources, and scores.
        """
        db = get_db_manager()
        with db.session_factory() as session:
            task = session.query(ResearchTask).filter_by(task_id=task_id).first()
            if not task:
                return {"task_id": task_id, "status": "not_found"}

            if task.status != "completed":
                return {"task_id": task_id, "status": task.status}

            return {
                "task_id": task_id,
                "status": "completed",
                "final_report": task.final_report,
                "charts": json.loads(task.chart_specs) if task.chart_specs else [],
                "sources": json.loads(task.sources) if task.sources else [],
                "quality_scores": json.loads(task.quality_scores) if task.quality_scores else {},
                "research_type": task.research_type,
            }

    async def get_logs(self, task_id: str) -> dict:
        """Get execution logs for a task.

        Args:
            task_id: The task UUID.

        Returns:
            dict with task_id and logs list.
        """
        db = get_db_manager()
        with db.session_factory() as session:
            task = session.query(ResearchTask).filter_by(task_id=task_id).first()
            if not task:
                return {"task_id": task_id, "logs": []}

            logs = json.loads(task.execution_logs) if task.execution_logs else []
            return {"task_id": task_id, "logs": logs}

    # ── Helpers ───────────────────────────────────────────────────────

    def _update_task_status(
        self, task_id: str, status: str, step: str, error: str | None = None
    ) -> None:
        """Update task status in database."""
        try:
            db = get_db_manager()
            with db.session_factory() as session:
                task = session.query(ResearchTask).filter_by(task_id=task_id).first()
                if task:
                    task.status = status
                    task.current_step = step
                    task.progress = self._estimate_progress(step)
                    if error:
                        task.error_message = error
                    task.updated_at = datetime.now(timezone.utc)
                    session.commit()
        except Exception as e:
            logger.error(f"[ResearchService] Failed to update task status: {e}")

    def _save_final_results(self, state: ResearchState) -> None:
        """Save final research results to database."""
        try:
            db = get_db_manager()
            with db.session_factory() as session:
                task = session.query(ResearchTask).filter_by(task_id=state.task_id).first()
                if task:
                    task.status = "completed"
                    task.current_step = "complete"
                    task.progress = 100
                    task.iteration_count = state.iteration_count
                    task.final_report = state.final_report
                    task.draft_report = state.draft_report
                    task.quality_scores = json.dumps(state.quality_scores, ensure_ascii=False)
                    task.chart_specs = json.dumps(state.chart_specs, ensure_ascii=False)
                    task.sources = json.dumps(state.cited_sources, ensure_ascii=False)
                    task.execution_logs = json.dumps(state.execution_logs, ensure_ascii=False)
                    task.updated_at = datetime.now(timezone.utc)
                    session.commit()
        except Exception as e:
            logger.error(f"[ResearchService] Failed to save results: {e}")

    def _load_state_from_db(self, task_id: str) -> ResearchState | None:
        """Load research state from database."""
        try:
            db = get_db_manager()
            with db.session_factory() as session:
                task = session.query(ResearchTask).filter_by(task_id=task_id).first()
                if task:
                    state = ResearchState(
                        task_id=task.task_id,
                        user_query=task.user_query,
                        research_type=task.research_type,
                    )
                    return state
        except Exception as e:
            logger.error(f"[ResearchService] Failed to load state from DB: {e}")
        return None

    @staticmethod
    def _estimate_progress(step: str) -> int:
        """Estimate progress percentage based on current step."""
        progress_map = {
            "init": 0,
            "ChiefArchitect": 5,
            "ChiefArchitect_complete": 15,
            "DeepScout": 20,
            "DeepScout_complete": 35,
            "DataAnalyst": 40,
            "DataAnalyst_complete": 55,
            "CodeWizard": 60,
            "CodeWizard_complete": 70,
            "LeadWriter": 75,
            "LeadWriter_complete": 85,
            "CriticMaster": 90,
            "CriticMaster_complete": 95,
            "complete": 100,
            "re_research": 50,
            "revise": 80,
        }
        return progress_map.get(step, 50)
