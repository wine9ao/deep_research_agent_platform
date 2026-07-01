"""LeadWriter Agent — LLM-powered Chinese research report generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..llm.client import get_llm_client
from ..state.research_state import ResearchState
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────

LEAD_WRITER_SYSTEM = """你是一名资深中文研究报告撰写专家（Lead Writer）。根据研究数据撰写结构清晰、专业、可读性强的中文研究报告。

## 写作要求

1. **结构清晰**：按给定大纲组织章节，每章有实质性内容
2. **数据驱动**：所有结论必须有数据支撑，引用具体数字
3. **专业术语**：使用行业标准术语，体现专业性
4. **客观中立**：陈述事实和数据，避免主观臆断
5. **引用来源**：在正文中标注信息来源
6. **可读性**：使用表格、列表增强可读性，段落不过长

## 输出格式

使用 Markdown 格式，包含：
- # 一级标题（报告标题）
- ## 二级标题（章节标题）
- ### 三级标题（小节标题）
- 表格（| 列1 | 列2 |）
- 列表（- 项目）
- **加粗** 用于强调关键数据
- ```chart 引用图表说明

## 报告标题

报告标题应直接使用用户的研究问题，不要添加额外修饰。

## 特别注意事项

- 如果某章节信息不足，明确指出"该部分信息尚待补充"，不要编造
- 图表位置用 `![图表说明](chart-path)` 或 `> 📊 [图表位置：图表标题]` 标注
- 每个章节至少150字
- 财务数据使用表格呈现
- 来源引用格式：[来源名称]
"""


class LeadWriter:
    """Lead Writer Agent — LLM generates the complete Chinese research report.

    Uses LLM for:
    - Full report generation based on all upstream research data
    - Natural, professional Chinese writing
    - Data-driven narrative with proper citations

    The LLM receives:
    - Research outline (from ChiefArchitect)
    - Facts and evidence (from DeepScout)
    - Analysis data and insights (from DataAnalyst)
    - Chart information (from CodeWizard)
    """

    name: str = "LeadWriter"
    description: str = "报告撰写Agent，使用LLM根据所有研究数据生成完整的中文Markdown研究报告。"

    def __init__(self) -> None:
        self._llm = get_llm_client()

    async def execute(self, state: ResearchState) -> ResearchState:
        """Generate the full research report using LLM.

        Args:
            state: ResearchState with all upstream data populated.

        Returns:
            Updated ResearchState with draft_report and cited_sources.
        """
        logger.info(f"[{self.name}] Starting LLM report generation...")
        state.add_log("LeadWriter", "execute", "start", {
            "outline_sections": len(state.outline),
            "facts_count": len(state.facts),
            "insights_count": len(state.analysis_insights),
        })

        # ── Build context for LLM ────────────────────────────────────
        context = self._build_research_context(state)

        # ── Call LLM to generate report ──────────────────────────────
        draft_report = await self._llm_generate_report(state, context)

        # ── Fallback if LLM failed ───────────────────────────────────
        if not draft_report or len(draft_report) < 100:
            logger.warning(f"[{self.name}] LLM report too short ({len(draft_report)} chars), using template fallback")
            draft_report = self._template_fallback(state)

        # ── Save report version ──────────────────────────────────────
        state.report_versions.append({
            "iteration": state.iteration_count,
            "report": draft_report,
            "timestamp": datetime.now().isoformat(),
        })

        state.draft_report = draft_report
        state.cited_sources = state.filtered_sources[:15]

        state.current_step = "LeadWriter_complete"
        state.update_timestamp()
        state.add_log("LeadWriter", "llm_generate", "complete", {
            "report_length": len(draft_report),
            "sections": len(state.outline),
            "sources_cited": len(state.cited_sources),
        })

        logger.info(f"[{self.name}] LLM report generated. Length={len(draft_report)} chars")
        return state

    # ── Build context ────────────────────────────────────────────────

    def _build_research_context(self, state: ResearchState) -> str:
        """Build a comprehensive context string for the LLM."""
        parts = []

        # Research meta
        parts.append(f"## 研究任务\n{state.user_query}\n研究类型：{state.research_type}")

        # Outline
        parts.append("\n## 报告大纲")
        for s in state.outline:
            parts.append(f"- {s.get('title', '')}: {s.get('description', '')}")

        # Facts from search
        if state.facts:
            parts.append(f"\n## 检索到的事实（共{len(state.facts)}条）")
            for f in state.facts[:20]:
                parts.append(f"- {f}")

        # Evidence
        if state.evidence_list:
            parts.append(f"\n## 信息来源（共{len(state.evidence_list)}条）")
            for e in state.evidence_list[:10]:
                parts.append(f"- [{e.get('source', '?')}] {e.get('title', '')} ({e.get('publish_time', '')})")

        # Financial data
        if state.financial_metrics:
            parts.append("\n## 公司财务指标")
            for company, metrics in state.financial_metrics.items():
                parts.append(f"\n### {company}")
                parts.append(f"- 最新营收：{metrics.get('latest_revenue', 'N/A')} 亿元")
                parts.append(f"- 最新净利润：{metrics.get('latest_profit', 'N/A')} 亿元")
                parts.append(f"- 毛利率：{_fmt_pct(metrics.get('latest_margin'))}")
                parts.append(f"- ROE：{_fmt_pct(metrics.get('latest_roe'))}")
                if metrics.get('cagr_revenue'):
                    parts.append(f"- 营收CAGR：{metrics['cagr_revenue']}%")

        # Industry metrics
        if state.industry_metrics:
            parts.append("\n## 行业指标")
            for ind, metrics in state.industry_metrics.items():
                parts.append(f"- {ind}：市场规模 {metrics.get('latest_size', 'N/A')} 亿元, 增长率 {_fmt_pct(metrics.get('latest_growth'))}")

        # Analysis insights
        if state.analysis_insights:
            parts.append(f"\n## 分析洞察（共{len(state.analysis_insights)}条）")
            for insight in state.analysis_insights[:15]:
                parts.append(f"- {insight}")

        # Charts
        if state.chart_specs:
            parts.append(f"\n## 生成的图表（共{len(state.chart_specs)}张）")
            for i, c in enumerate(state.chart_specs):
                parts.append(f"{i + 1}. {c.get('title', '')}（{c.get('chart_type', '')}）")

        # Visualization summary
        if state.visualization_summary:
            parts.append(f"\n{state.visualization_summary}")

        # Sources to cite
        if state.filtered_sources:
            parts.append(f"\n## 需要引用的来源（共{len(state.filtered_sources)}条）")
            for i, src in enumerate(state.filtered_sources[:12]):
                parts.append(f"{i + 1}. {src.get('title', '')} — {src.get('source', '')} ({src.get('publish_time', '')})")

        return "\n".join(parts)

    # ── LLM generation ───────────────────────────────────────────────

    async def _llm_generate_report(self, state: ResearchState, context: str) -> str:
        """Call LLM to generate the complete report."""
        user_message = f"""请根据以下研究数据，撰写一份完整的中文研究报告。

{context[:8000]}

要求：
1. 严格按照大纲结构组织章节
2. 每个章节至少150字实质性内容
3. 财务数据使用表格呈现
4. 引用具体数字和来源
5. 图表位置用 > 📊 [图表标题] 标注
6. 结论基于数据，不主观臆断
7. 信息不足的章节明确标注"""

        try:
            messages = [
                {"role": "system", "content": LEAD_WRITER_SYSTEM},
                {"role": "user", "content": user_message},
            ]
            report = await self._llm.chat(messages, max_tokens=8192)
            logger.info(f"[{self.name}] LLM generated report: {len(report)} chars")
            return report
        except Exception as e:
            logger.error(f"[{self.name}] LLM report generation failed: {e}")
            return ""

    # ── Template fallback ─────────────────────────────────────────────

    def _template_fallback(self, state: ResearchState) -> str:
        """Template-based fallback when LLM is unavailable."""
        sections = [f"# {state.user_query}\n"]
        sections.append(f"> 研究类型：{state.research_type} | 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 任务ID：{state.task_id[:8]}\n")

        for section in state.outline:
            title = section.get("title", "")
            desc = section.get("description", "")
            content = f"## {title}\n\n*{desc}*\n\n"

            # Add relevant facts
            relevant = [f for f in state.facts[:5] if len(f) > 15]
            if relevant:
                for f in relevant[:3]:
                    content += f"- {f}\n"
            else:
                content += "该章节内容基于研究数据和行业知识生成。具体数据请参考相关图表和附录。\n"
            sections.append(content)

        # Sources
        sections.append("## 附录：数据来源与参考资料\n")
        for i, src in enumerate(state.filtered_sources[:10]):
            sections.append(f"{i + 1}. **{src.get('title', '?')}** — {src.get('source', '?')} ({src.get('publish_time', '')})")

        return "\n\n".join(sections)


def _fmt_pct(val: float | None) -> str:
    """Format a decimal as percentage string."""
    if val is None:
        return "N/A"
    return f"{round(val * 100, 1)}%"
