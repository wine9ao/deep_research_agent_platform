"""Research Router — determines the next step after CriticMaster review."""

from __future__ import annotations

from ..state.research_state import ResearchState
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ResearchRouter:
    """Routes the workflow based on CriticMaster's quality review.

    Routing rules:
    - 'complete' → End the workflow, finalize report
    - 're_research' → Return to DeepScout for more information
    - 'revise' → Return to LeadWriter for report revision

    Enforces max_iterations cap to prevent infinite loops.
    """

    # Route destinations
    COMPLETE = "complete"
    RE_RESEARCH = "re_research"
    REVISE = "revise"

    def __init__(self, max_iterations: int = 3) -> None:
        self.max_iterations = max_iterations

    def route(self, state: ResearchState) -> str:
        """Determine the next step in the research workflow.

        Args:
            state: Current ResearchState after CriticMaster review.

        Returns:
            String indicating the next destination:
            'complete', 're_research', or 'revise'
        """
        decision = state.route_decision
        iteration = state.iteration_count

        logger.info(f"[Router] Iteration {iteration}/{self.max_iterations}, decision: {decision}")

        if decision == self.COMPLETE:
            logger.info("[Router] Quality passed. Finalizing research.")
            state.final_report = state.draft_report
            return self.COMPLETE

        # ── Detect declining scores: stop if score dropped twice in a row ──
        recent_scores = [
            fb.get("scores", {}).get("final_score", 0)
            for fb in state.review_feedback[-3:]
        ]
        if len(recent_scores) >= 2 and recent_scores[-1] < recent_scores[-2]:
            logger.warning(
                f"[Router] Scores declining ({recent_scores}), forcing completion. "
                "Additional research is not improving quality."
            )
            state.route_decision = self.COMPLETE
            if "仍需人工复核" not in state.draft_report:
                state.draft_report += (
                    "\n\n---\n> ⚠️ **提示**：多轮优化后评分未见提升，建议人工复核关键数据和结论。\n"
                )
            state.final_report = state.draft_report
            return self.COMPLETE

        if iteration >= self.max_iterations:
            logger.warning(
                f"[Router] Max iterations ({self.max_iterations}) reached. "
                f"Forcing completion."
            )
            # Force complete
            state.route_decision = self.COMPLETE
            if "仍需人工复核" not in state.draft_report:
                state.draft_report += (
                    "\n\n---\n> ⚠️ **提示**：本研究已达到最大迭代次数限制"
                    f"（{self.max_iterations}次），部分内容可能需要人工复核。\n"
                )
            state.final_report = state.draft_report
            return self.COMPLETE

        if decision == self.RE_RESEARCH:
            logger.info("[Router] Insufficient information. Routing to Re-Research.")
            state.iteration_count += 1
            state.add_log("Router", "route", "re_research", {
                "iteration": state.iteration_count,
                "reason": "信息不足，需要补充检索",
            })
            return self.RE_RESEARCH

        if decision == self.REVISE:
            logger.info("[Router] Report needs revision. Routing to Revise.")
            state.iteration_count += 1
            state.add_log("Router", "route", "revise", {
                "iteration": state.iteration_count,
                "reason": "报告需要修改",
            })
            return self.REVISE

        # Default: complete
        logger.warning(f"[Router] Unknown decision '{decision}', defaulting to complete.")
        return self.COMPLETE
