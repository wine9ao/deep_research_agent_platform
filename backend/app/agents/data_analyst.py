"""DataAnalyst Agent — LLM-powered financial and industry data analysis."""

from __future__ import annotations

import json
from typing import Any

from ..llm.client import get_llm_client
from ..state.research_state import ResearchState
from ..tools.financial_api import FinancialDataAPITool
from ..tools.data_analysis import DataAnalysisTool
from ..tools.text2sql import Text2SQLTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── LLM prompt ────────────────────────────────────────────────────────────

DATA_ANALYST_SYSTEM = """你是一名资深数据分析师（Data Analyst），负责从结构化数据中提取洞察。

你的任务：
1. 分析查询中涉及的公司和行业
2. 解读财务数据和行业指标
3. 识别关键趋势、异常值和投资信号
4. 生成分析洞察和图表建议

返回JSON格式：
```json
{
  "identified_companies": ["公司1", "公司2"],
  "identified_industries": ["行业1"],
  "analysis_insights": [
    "洞察1：具体发现和含义",
    "洞察2：趋势分析",
    "洞察3：对比结论"
  ],
  "chart_suggestions": [
    {"chart_type": "bar", "title": "2025年营收对比", "reason": "直观对比各公司营收规模"},
    {"chart_type": "radar", "title": "多维竞争力对比", "reason": "综合评估企业能力"}
  ],
  "key_findings": "核心发现总结（2-3句话）"
}
```

图表类型(echarts): line, bar, pie, radar, horizontal_bar, financial_trend

分析维度参考：
- 营收规模与增长趋势
- 盈利能力（毛利率、净利率、ROE）
- 市场份额变化
- 资产负债结构
- 行业增速对比
- 估值水平
"""


class DataAnalyst:
    """Data Analyst Agent — LLM-powered structured data analysis.

    Uses LLM for:
    - Entity recognition (companies, industries, metrics)
    - Data interpretation and insight generation
    - Chart recommendation

    Uses Tools for:
    - Financial data retrieval (FinancialDataAPITool)
    - Statistical computation (DataAnalysisTool)
    - Text2SQL (Text2SQLTool)
    """

    name: str = "DataAnalyst"
    description: str = "数据分析Agent，使用LLM识别实体、解读数据并生成分析洞察。"

    def __init__(self) -> None:
        self._financial_api = FinancialDataAPITool()
        self._data_analysis = DataAnalysisTool()
        self._text2sql = Text2SQLTool()
        self._llm = get_llm_client()

    async def execute(self, state: ResearchState) -> ResearchState:
        """Execute LLM-powered data analysis."""
        logger.info(f"[{self.name}] Starting LLM data analysis for: {state.user_query[:60]}...")
        state.add_log("DataAnalyst", "execute", "start", {"query": state.user_query[:100]})

        # ── Step 1: LLM identifies entities ──────────────────────────
        entities = await self._llm_identify_entities(state)

        companies = entities.get("identified_companies", [])
        industries = entities.get("identified_industries", [])

        # Fallback: keyword matching if LLM didn't find entities
        if not companies:
            known = FinancialDataAPITool.get_available_companies()
            companies = [c for c in known if c in state.user_query]
        if not industries:
            known = FinancialDataAPITool.get_available_industries()
            industries = [i for i in known if i in state.user_query]

        logger.info(f"[{self.name}] LLM identified: companies={companies}, industries={industries}")
        state.add_log("DataAnalyst", "llm_identify", "entities", {
            "companies": companies, "industries": industries,
        })

        # ── Step 2: Query financial data via tools ───────────────────
        all_company_data, all_industry_data = await self._fetch_data(companies, industries)

        # ── Step 3: Statistical analysis via tools ───────────────────
        analysis_insights, financial_metrics, industry_metrics = await self._run_statistics(
            all_company_data, all_industry_data,
        )

        # ── Step 4: LLM generates insights and chart suggestions ─────
        llm_insights = await self._llm_generate_insights(
            state, companies, industries, financial_metrics, industry_metrics,
        )

        analysis_insights.extend(llm_insights.get("analysis_insights", []))
        chart_suggestions = llm_insights.get("chart_suggestions", [])

        # Build chart requirements
        chart_requirements = [
            {"chart_type": cs["chart_type"], "title": cs["title"], "description": cs.get("reason", ""), "data_source": "financial_api"}
            for cs in chart_suggestions
        ]

        # ── Step 5: Store results ────────────────────────────────────
        state.structured_data = {"companies": all_company_data, "industries": all_industry_data}
        state.financial_metrics = financial_metrics
        state.industry_metrics = industry_metrics
        state.analysis_insights = analysis_insights
        state.chart_requirements = chart_requirements

        state.current_step = "DataAnalyst_complete"
        state.update_timestamp()
        state.add_log("DataAnalyst", "execute", "complete", {
            "companies_analyzed": len(companies),
            "industries_analyzed": len(industries),
            "llm_insights": len(llm_insights.get("analysis_insights", [])),
            "charts_requested": len(chart_requirements),
        })

        logger.info(f"[{self.name}] Complete. Insights={len(analysis_insights)}, Charts={len(chart_requirements)}")
        return state

    # ── LLM: Entity identification ───────────────────────────────────

    async def _llm_identify_entities(self, state: ResearchState) -> dict:
        """LLM identifies companies and industries from the query."""
        available_companies = FinancialDataAPITool.get_available_companies()
        available_industries = FinancialDataAPITool.get_available_industries()

        prompt = f"""研究问题：{state.user_query}

可用的公司数据：{', '.join(available_companies)}
可用的行业数据：{', '.join(available_industries)}

请识别研究问题中涉及的公司和行业（只从可用列表中选择，如果没有匹配的，返回空列表）。

返回JSON：{{"identified_companies": [...], "identified_industries": [...]}}"""

        try:
            messages = [
                {"role": "system", "content": "你是一个实体识别助手。只返回JSON，不要其他内容。"},
                {"role": "user", "content": prompt},
            ]
            result = await self._llm.chat_json(messages)
            if result.get("_parse_error"):
                return {"identified_companies": [], "identified_industries": []}
            return result
        except Exception as e:
            logger.warning(f"[{self.name}] LLM entity identification failed: {e}")
            return {"identified_companies": [], "identified_industries": []}

    # ── LLM: Insight generation ──────────────────────────────────────

    async def _llm_generate_insights(
        self, state: ResearchState, companies: list[str], industries: list[str],
        financial_metrics: dict, industry_metrics: dict,
    ) -> dict:
        """LLM interprets the data and generates insights."""
        # Build data summary for LLM
        data_summary = "## 公司财务数据摘要\n"
        for company, metrics in financial_metrics.items():
            data_summary += f"- {company}: {json.dumps(metrics, ensure_ascii=False)}\n"

        data_summary += "\n## 行业数据摘要\n"
        for ind, metrics in industry_metrics.items():
            data_summary += f"- {ind}: {json.dumps(metrics, ensure_ascii=False)}\n"

        prompt = f"""研究问题：{state.user_query}
研究类型：{state.research_type}

{data_summary}

请基于以上数据，生成分析洞察和图表建议。"""

        try:
            messages = [
                {"role": "system", "content": DATA_ANALYST_SYSTEM},
                {"role": "user", "content": prompt[:4000]},
            ]
            result = await self._llm.chat_json(messages)
            if result.get("_parse_error"):
                return {"analysis_insights": [], "chart_suggestions": []}
            logger.info(f"[{self.name}] LLM generated {len(result.get('analysis_insights', []))} insights")
            return result
        except Exception as e:
            logger.warning(f"[{self.name}] LLM insight generation failed: {e}")
            return {"analysis_insights": [], "chart_suggestions": []}

    # ── Tool-based data fetching ─────────────────────────────────────

    async def _fetch_data(self, companies: list[str], industries: list[str]) -> tuple[dict, dict]:
        """Fetch data from financial API tool."""
        all_company_data = {}
        all_industry_data = {}

        if companies:
            r = await self._financial_api.run({"query_type": "company", "company_names": companies})
            if r["success"]:
                all_company_data = r["data"]

        if industries:
            r = await self._financial_api.run({"query_type": "industry", "industry_names": industries})
            if r["success"]:
                all_industry_data = r["data"]

        # Default to all if nothing found
        if not all_company_data and not companies:
            r = await self._financial_api.run({"query_type": "company", "company_names": ["宁德时代", "比亚迪"]})
            if r["success"]:
                all_company_data = r["data"]

        return all_company_data, all_industry_data

    # ── Tool-based statistics ────────────────────────────────────────

    async def _run_statistics(
        self, company_data: dict, industry_data: dict,
    ) -> tuple[list[str], dict, dict]:
        """Run statistical analysis tools."""
        insights: list[str] = []
        financial_metrics: dict = {}
        industry_metrics: dict = {}

        if company_data:
            flattened = []
            for cname, records in company_data.items():
                for r in records:
                    r_copy = dict(r)
                    r_copy["company_name"] = cname
                    flattened.append(r_copy)

            # YoY growth
            yoy = await self._data_analysis.run({
                "operation": "yoy_growth", "data": flattened,
                "value_column": "revenue", "group_column": "company_name", "year_column": "year",
            })
            if yoy["success"]:
                insights.extend(yoy["data"].get("insights", []))

            # CAGR
            cagr = await self._data_analysis.run({
                "operation": "cagr", "data": flattened,
                "value_column": "revenue", "group_column": "company_name", "year_column": "year",
            })
            if cagr["success"]:
                insights.extend(cagr["data"].get("insights", []))

            # Build metrics dict
            financial_metrics = {
                cname: {
                    "latest_revenue": records[-1].get("revenue"),
                    "latest_profit": records[-1].get("net_profit"),
                    "latest_margin": records[-1].get("gross_margin"),
                    "latest_roe": records[-1].get("roe"),
                    "cagr_revenue": self._calc_cagr_simple(records, "revenue"),
                    "cagr_profit": self._calc_cagr_simple(records, "net_profit"),
                }
                for cname, records in company_data.items()
            }

        if industry_data:
            ind_flat = []
            for iname, records in industry_data.items():
                for r in records:
                    r_copy = dict(r)
                    r_copy["industry_name"] = iname
                    ind_flat.append(r_copy)

            ind_yoy = await self._data_analysis.run({
                "operation": "yoy_growth", "data": ind_flat,
                "value_column": "market_size", "group_column": "industry_name", "year_column": "year",
            })
            if ind_yoy["success"]:
                insights.extend(ind_yoy["data"].get("insights", []))

            industry_metrics = {
                iname: {
                    "latest_size": records[-1].get("market_size"),
                    "latest_growth": records[-1].get("growth_rate"),
                    "cagr": self._calc_cagr_simple(records, "market_size"),
                }
                for iname, records in industry_data.items()
            }

        return insights, financial_metrics, industry_metrics

    @staticmethod
    def _calc_cagr_simple(records: list[dict], col: str) -> float | None:
        if not records or len(records) < 2:
            return None
        sorted_recs = sorted(records, key=lambda r: r.get("year", 0))
        first_val, last_val = sorted_recs[0].get(col), sorted_recs[-1].get(col)
        years = sorted_recs[-1].get("year", 0) - sorted_recs[0].get("year", 0)
        if first_val and last_val and first_val > 0 and years > 0:
            return round(((last_val / first_val) ** (1 / years) - 1) * 100, 1)
        return None
