"""Research Graph — LangGraph-style workflow orchestration for the 6-agent pipeline.

Implements the complete research workflow:
START → ChiefArchitect → DeepScout → DataAnalyst → CodeWizard → LeadWriter → CriticMaster
       → route_by_review → [Complete | Re-Research → DeepScout | Revise → LeadWriter]

With max_iterations enforcement and Checkpoint support.
"""

from __future__ import annotations

from typing import Any, Callable

from ..agents.chief_architect import ChiefArchitect
from ..agents.deep_scout import DeepScout
from ..agents.data_analyst import DataAnalyst
from ..agents.code_wizard import CodeWizard
from ..agents.lead_writer import LeadWriter
from ..agents.critic_master import CriticMaster
from ..state.research_state import ResearchState
from ..state.checkpoint import CheckpointManager
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── Node names ───────────────────────────────────────────────────────────

NODE_CHIEF = "ChiefArchitect"
NODE_SCOUT = "DeepScout"
NODE_ANALYST = "DataAnalyst"
NODE_CODER = "CodeWizard"
NODE_WRITER = "LeadWriter"
NODE_CRITIC = "CriticMaster"


class ResearchGraph:
    """Orchestrates the 6-agent research pipeline with smart routing.

    Implements a LangGraph-compatible state graph pattern where each
    agent is a node that reads and updates the shared ResearchState.

    The graph follows this flow:
    1. ChiefArchitect plans the research
    2. DeepScout searches for information
    3. DataAnalyst queries and analyzes data
    4. CodeWizard generates charts
    5. LeadWriter composes the report
    6. CriticMaster reviews quality
    7. Router decides: Complete, Re-Research, or Revise

    Usage:
        graph = ResearchGraph()
        state = ResearchState(user_query="分析动力电池行业")
        final_state = await graph.run(state)
    """

    def __init__(
        self,
        max_iterations: int = 3,
        checkpoint_manager: CheckpointManager | None = None,
        progress_callback: Callable[[str, dict], None] | None = None,
    ) -> None:
        """Initialize the research graph with all agents.

        Args:
            max_iterations: Maximum number of research-review cycles.
            checkpoint_manager: Optional checkpoint manager for state persistence.
            progress_callback: Optional callback for progress updates.
              Called with (step_name: str, details: dict).
        """
        self.max_iterations = max_iterations
        self.checkpoint = checkpoint_manager
        self.progress_callback = progress_callback

        # Initialize agents
        self.chief = ChiefArchitect()
        self.scout = DeepScout()
        self.analyst = DataAnalyst()
        self.coder = CodeWizard()
        self.writer = LeadWriter()
        self.critic = CriticMaster()

        # Build the execution pipeline
        self._nodes: list[tuple[str, Callable]] = [
            (NODE_CHIEF, self.chief.execute),
            (NODE_SCOUT, self.scout.execute),
            (NODE_ANALYST, self.analyst.execute),
            (NODE_CODER, self.coder.execute),
            (NODE_WRITER, self.writer.execute),
            (NODE_CRITIC, self.critic.execute),
        ]

    async def run(self, state: ResearchState) -> ResearchState:
        """Execute the full research pipeline.

        Args:
            state: Initial ResearchState with at least user_query set.

        Returns:
            Final ResearchState with final_report populated.
        """
        state.max_iterations = self.max_iterations
        logger.info(f"[ResearchGraph] Starting research pipeline for: {state.user_query[:80]}...")
        state.add_log("ResearchGraph", "pipeline", "start", {
            "query": state.user_query[:100],
            "max_iterations": self.max_iterations,
        })

        try:
            # ── Save initial checkpoint ──
            if self.checkpoint:
                await self.checkpoint.save(state)

            # ── Phase 1: Forward pipeline ─────────────────────────────
            state = await self._execute_forward_pipeline(state)

            # ── Phase 2: Review & Route loop ──────────────────────────
            state = await self._review_loop(state)

            # ── Final checkpoint ──────────────────────────────────────
            state.current_step = "complete"
            state.update_timestamp()
            if self.checkpoint:
                await self.checkpoint.save(state)

            self._notify_progress("complete", {"task_id": state.task_id})
            logger.info(f"[ResearchGraph] Pipeline complete. Task={state.task_id[:8]}")
            state.add_log("ResearchGraph", "pipeline", "complete", {
                "task_id": state.task_id,
                "iterations": state.iteration_count,
                "report_length": len(state.final_report),
                "final_score": state.quality_scores.get("final_score", 0),
            })

        except Exception as e:
            logger.error(f"[ResearchGraph] Pipeline error: {e}", exc_info=True)
            state.add_error(f"Pipeline error: {e}")
            state.current_step = "error"

        return state

    async def _execute_forward_pipeline(self, state: ResearchState) -> ResearchState:
        """Execute the 6-agent forward pipeline in sequence."""
        for node_name, node_fn in self._nodes:
            logger.info(f"[ResearchGraph] Executing node: {node_name}")
            state.current_step = node_name
            self._notify_progress(node_name, {"step": node_name})

            try:
                state = await node_fn(state)
                state.add_log("ResearchGraph", "node_complete", node_name, {})

                # Save checkpoint after each node
                if self.checkpoint:
                    await self.checkpoint.save(state)

            except Exception as e:
                logger.error(f"[ResearchGraph] Node {node_name} failed: {e}", exc_info=True)
                state.add_error(f"Node {node_name} failed: {e}")
                # Continue with next node if possible
                state.current_step = f"{node_name}_error"

        return state

    async def _review_loop(self, state: ResearchState) -> ResearchState:
        """Run the review-routing loop until complete or max iterations."""
        from .router import ResearchRouter
        router = ResearchRouter(self.max_iterations)

        while True:
            route = router.route(state)

            if route == router.COMPLETE:
                logger.info("[ResearchGraph] Review loop: Complete")
                break

            elif route == router.RE_RESEARCH:
                logger.info(f"[ResearchGraph] Review loop: Re-Research (iteration {state.iteration_count})")
                self._notify_progress("re_research", {"iteration": state.iteration_count})

                # Re-run DeepScout → DataAnalyst → CodeWizard → LeadWriter → CriticMaster
                state = await self.scout.execute(state)
                state = await self.analyst.execute(state)
                state = await self.coder.execute(state)
                state = await self.writer.execute(state)
                state = await self.critic.execute(state)

                if self.checkpoint:
                    await self.checkpoint.save(state)

            elif route == router.REVISE:
                logger.info(f"[ResearchGraph] Review loop: Revise (iteration {state.iteration_count})")
                self._notify_progress("revise", {"iteration": state.iteration_count})

                # Re-run LeadWriter → CriticMaster
                state = await self.writer.execute(state)
                state = await self.critic.execute(state)

                if self.checkpoint:
                    await self.checkpoint.save(state)

            else:
                logger.warning(f"[ResearchGraph] Unknown route: {route}")
                break

        return state

    def _notify_progress(self, step: str, details: dict) -> None:
        """Notify progress via callback if set."""
        if self.progress_callback:
            try:
                self.progress_callback(step, details)
            except Exception:
                pass  # Don't let callback errors break the pipeline

    # ── Convenience ───────────────────────────────────────────────────

    async def run_query(self, query: str, research_type: str = "") -> ResearchState:
        """Convenience method: create state and run full pipeline.

        Args:
            query: Research question.
            research_type: Optional research type hint.

        Returns:
            Final ResearchState.
        """
        state = ResearchState(user_query=query)
        if research_type:
            state.research_type = research_type
        return await self.run(state)

    @classmethod
    async def quick_run(cls, query: str) -> str:
        """Quick run returning just the final report string.

        Args:
            query: Research question.

        Returns:
            Final report as markdown string.
        """
        graph = cls(max_iterations=3)
        state = await graph.run_query(query)
        return state.final_report or state.draft_report or "报告生成失败。"
