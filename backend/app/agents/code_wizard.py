"""CodeWizard Agent — LLM-enhanced chart generation and code execution."""

from __future__ import annotations

import json
from typing import Any

from ..llm.client import get_llm_client
from ..state.research_state import ResearchState
from ..tools.chart_generation import ChartGenerationTool
from ..tools.python_execution import PythonExecutionTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── LLM prompt for chart data preparation ─────────────────────────────────

CODE_WIZARD_SYSTEM = """你是一名数据可视化专家（Code Wizard）。根据提供的公司和行业数据，生成ECharts图表的数据配置。

对于每个图表需求，返回：
```json
{
  "charts": [
    {
      "chart_type": "bar",
      "title": "图表标题",
      "labels": ["标签1", "标签2"],
      "series_data": [{"name": "系列名", "data": [值1, 值2]}],
      "chart_index": 0
    }
  ],
  "visualization_summary": "本研究生成了N张图表，包括..."
}
```

图表类型映射:
- bar: 柱状图 (series_data中data为数值数组)
- line: 折线图
- pie: 饼图 (series_data中每项为{"name": "A", "value": 40})
- radar: 雷达图 (data为5-6个0-100的数值)
- horizontal_bar: 横向柱状图
- financial_trend: 财务趋势图 (series_data中每项带type和yAxisName)
"""


class CodeWizard:
    """Code Wizard Agent — LLM-assisted chart data preparation.

    Uses LLM for:
    - Mapping analytical data to chart-ready formats
    - Generating visualization summaries

    Uses Tools for:
    - ChartGenerationTool (ECharts spec generation)
    - PythonExecutionTool (safe data processing)
    """

    name: str = "CodeWizard"
    description: str = "代码与可视化Agent，使用LLM辅助图表数据映射和可视化摘要生成。"

    def __init__(self) -> None:
        self._chart_gen = ChartGenerationTool()
        self._py_exec = PythonExecutionTool()
        self._llm = get_llm_client()

    async def execute(self, state: ResearchState) -> ResearchState:
        """Generate charts with LLM-assisted data preparation."""
        logger.info(f"[{self.name}] Starting LLM-assisted chart generation...")
        state.add_log("CodeWizard", "execute", "start", {
            "chart_requirements": len(state.chart_requirements),
        })

        chart_specs: list[dict] = []
        chart_paths: list[str] = []
        company_data = state.structured_data.get("companies", {})
        industry_data = state.structured_data.get("industries", {})

        # ── LLM prepares chart data ──────────────────────────────────
        charts_data = await self._llm_prepare_chart_data(state, company_data, industry_data)

        # ── Generate each chart via ChartGenerationTool ───────────────
        for i, chart_cfg in enumerate(charts_data.get("charts", [])):
            chart_type = chart_cfg.get("chart_type", "bar")
            title = chart_cfg.get("title", f"图表{i + 1}")
            labels = chart_cfg.get("labels", [])
            series_data = chart_cfg.get("series_data", [])

            logger.debug(f"[{self.name}] Generating chart {i + 1}: {title} ({chart_type})")
            state.add_log("CodeWizard", "generate_chart", f"chart_{i + 1}", {
                "type": chart_type, "title": title, "llm_prepared": True,
            })

            chart_result = await self._chart_gen.run({
                "chart_type": chart_type,
                "title": title,
                "labels": labels,
                "series_data": series_data,
                "subtitle": chart_cfg.get("description", ""),
            })

            if chart_result["success"] and chart_result["data"]:
                spec = chart_result["data"]["echarts_option"]
                chart_specs.append({
                    "chart_type": chart_type,
                    "title": title,
                    "echarts_option": spec,
                    "description": chart_cfg.get("description", ""),
                })
                chart_paths.append(f"#chart-{i + 1}")

        # Fallback: use rule-based if LLM didn't produce charts
        if not chart_specs:
            chart_specs, chart_paths = await self._fallback_charts(state, company_data, industry_data)

        state.chart_specs = chart_specs
        state.chart_paths = chart_paths
        state.visualization_summary = charts_data.get(
            "visualization_summary",
            f"本研究共生成 {len(chart_specs)} 张图表。",
        )

        state.current_step = "CodeWizard_complete"
        state.update_timestamp()
        state.add_log("CodeWizard", "execute", "complete", {
            "charts_generated": len(chart_specs),
            "llm_prepared": True,
        })

        logger.info(f"[{self.name}] Complete. Generated {len(chart_specs)} charts.")
        return state

    # ── LLM: Chart data preparation ──────────────────────────────────

    async def _llm_prepare_chart_data(
        self, state: ResearchState, company_data: dict, industry_data: dict,
    ) -> dict:
        """Use LLM to prepare chart-ready data from raw analysis data."""
        # Build data summary
        data_summary = ""
        for cname, records in company_data.items():
            latest = [r for r in records if r.get("year") == 2025]
            if latest:
                data_summary += f"{cname} 2025: {json.dumps(latest[0], ensure_ascii=False)}\n"

        for iname, records in industry_data.items():
            data_summary += f"\n{iname} trends:\n"
            for r in records:
                data_summary += f"  {r.get('year')}: market_size={r.get('market_size')}, growth={r.get('growth_rate')}\n"

        chart_requests = "\n".join(
            f"- [{cr.get('chart_type')}] {cr.get('title')}: {cr.get('description', '')}"
            for cr in state.chart_requirements
        ) if state.chart_requirements else "- bar: 营收对比图"

        prompt = f"""研究问题：{state.user_query}

可用公司数据：
{data_summary[:3000]}

图表需求：
{chart_requests}

请为每个图表需求准备labels和series_data。"""

        try:
            messages = [
                {"role": "system", "content": CODE_WIZARD_SYSTEM},
                {"role": "user", "content": prompt},
            ]
            result = await self._llm.chat_json(messages)
            if not result.get("_parse_error") and result.get("charts"):
                logger.info(f"[{self.name}] LLM prepared {len(result['charts'])} charts")
                return result
        except Exception as e:
            logger.warning(f"[{self.name}] LLM chart prep failed: {e}")

        return {"charts": [], "visualization_summary": ""}

    # ── Fallback chart generation ────────────────────────────────────

    async def _fallback_charts(
        self, state: ResearchState, company_data: dict, industry_data: dict,
    ) -> tuple[list[dict], list[str]]:
        """Rule-based chart generation fallback."""
        specs = []
        paths = []
        companies = list(company_data.keys())

        if companies:
            # Revenue bar chart
            labels = companies
            revenues = []
            for c in companies:
                records = company_data.get(c, [])
                latest = [r for r in records if r.get("year") == 2025]
                revenues.append(latest[0].get("revenue", 0) if latest else 0)

            result = await self._chart_gen.run({
                "chart_type": "bar",
                "title": "2025年核心企业营收对比（亿元）",
                "labels": labels,
                "series_data": [{"name": "营收（亿元）", "data": revenues}],
            })
            if result["success"] and result["data"]:
                specs.append({"chart_type": "bar", "title": "营收对比", "echarts_option": result["data"]["echarts_option"]})
                paths.append("#chart-1")

        return specs, paths
