"""ResearchState — global Pydantic state shared by all agents in the Deep Research platform.

All fields carry sensible defaults so agents can be spun up incrementally.  The state
is designed to be serialised/deserialised via Pydantic v2 (``model_dump`` /
``model_validate``) and checked by the ``CheckpointManager``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResearchState(BaseModel):
    """Central state object passed between every agent in a research run."""

    # ------------------------------------------------------------------
    # Identity & lifecycle
    # ------------------------------------------------------------------
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_query: str = ""
    research_type: Optional[str] = Field(
        default=None,
        description="行业分析 / 公司分析 / 财务分析 / 竞品分析 / 政策分析 / 综合研究",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    current_step: str = Field(default="init", description="Current pipeline step name.")
    iteration_count: int = Field(default=0, ge=0)
    max_iterations: int = Field(default=3, ge=1)

    # ------------------------------------------------------------------
    # Research planning
    # ------------------------------------------------------------------
    research_questions: list[str] = Field(default_factory=list)
    outline: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Each entry: {title: str, description: str}.",
    )
    search_plan: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Each entry: {query: str, source_type: str, priority: str}.",
    )
    data_requirements: list[str] = Field(default_factory=list)
    expected_charts: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Search & evidence
    # ------------------------------------------------------------------
    raw_search_results: list[dict[str, Any]] = Field(default_factory=list)
    filtered_sources: list[dict[str, Any]] = Field(default_factory=list)
    evidence_list: list[dict[str, Any]] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Structured data (domain-specific)
    # ------------------------------------------------------------------
    structured_data: dict[str, Any] = Field(default_factory=dict)
    financial_metrics: dict[str, Any] = Field(default_factory=dict)
    industry_metrics: dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Analysis & charts
    # ------------------------------------------------------------------
    analysis_insights: list[str] = Field(default_factory=list)
    chart_requirements: list[dict[str, Any]] = Field(default_factory=list)
    chart_specs: list[dict[str, Any]] = Field(default_factory=list)
    chart_paths: list[str] = Field(default_factory=list)
    visualization_summary: str = ""

    # ------------------------------------------------------------------
    # Reports & sources
    # ------------------------------------------------------------------
    draft_report: str = ""
    final_report: str = ""
    cited_sources: list[dict[str, Any]] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Review & quality
    # ------------------------------------------------------------------
    review_feedback: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Each entry is a feedback dict from the reviewer agent.",
    )
    quality_scores: dict[str, float] = Field(
        default_factory=lambda: {
            "completeness": 0.0,
            "factuality": 0.0,
            "logic": 0.0,
            "citation": 0.0,
            "data": 0.0,
            "readability": 0.0,
            "final": 0.0,
        }
    )
    route_decision: str = Field(
        default="complete",
        description="Routing decision: complete / re_research / revise.",
    )

    # ------------------------------------------------------------------
    # Memory & logs
    # ------------------------------------------------------------------
    memory_context: dict[str, Any] = Field(default_factory=dict)
    execution_logs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Each log: {step: str, agent: str, action: str, "
        "timestamp: str, details: str}.",
    )
    errors: list[str] = Field(default_factory=list)
    report_versions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Each version: {iteration: int, report: str, timestamp: str}.",
    )

    # ==================================================================
    # Convenience methods
    # ==================================================================

    def add_log(
        self,
        step: str,
        agent: str,
        action: str,
        details: str = "",
    ) -> None:
        """Append a structured log entry to ``execution_logs``."""
        self.execution_logs.append(
            {
                "step": step,
                "agent": agent,
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": details,
            }
        )

    def add_error(self, error: str) -> None:
        """Record an error message."""
        self.errors.append(error)

    def add_report_version(self, report: str) -> None:
        """Save a snapshot of the report at the current iteration."""
        self.report_versions.append(
            {
                "iteration": self.iteration_count,
                "report": report,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire state to a plain Python dictionary.

        Uses ``model_dump`` from Pydantic v2, which is the recommended
        replacement for the deprecated ``.dict()`` method.
        """
        return self.model_dump()

    def update_timestamp(self) -> None:
        """Set ``updated_at`` to the current UTC time."""
        self.updated_at = datetime.now(timezone.utc).isoformat()

    # ==================================================================
    # Pydantic v2 helpers (alternative constructors)
    # ==================================================================

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchState:
        """Reconstruct a ``ResearchState`` from a plain dict (e.g. from DB)."""
        return cls.model_validate(data)
