"""ChiefArchitect Agent — LLM-powered task understanding and research planning."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from ..llm.client import get_llm_client
from ..state.research_state import ResearchState
from ..tools.query_expansion import QueryExpansionTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────

CHIEF_ARCHITECT_SYSTEM = """你是一名资深研究规划师（Chief Architect），负责为研究任务制定完整的执行计划。

你的职责：
1. 理解用户的研究问题
2. 判断研究类型（行业分析/公司分析/财务分析/竞品分析/政策分析/综合研究）
3. 将研究问题拆解为3-5个子问题
4. 生成研究大纲（8-11个章节，使用中文标题）
5. 确定数据需求和预期图表类型

请严格按以下JSON格式返回，不要包含任何其他文字：
```json
{
  "research_type": "行业分析",
  "research_questions": ["子问题1", "子问题2", "子问题3"],
  "outline": [
    {"title": "一、研究摘要", "description": "..."},
    {"title": "二、行业背景", "description": "..."}
  ],
  "data_requirements": ["需求1", "需求2"],
  "expected_charts": ["市场规模趋势图（折线图）", "市场份额分布图（饼图）"],
  "key_entities": {
    "companies": ["公司名1", "公司名2"],
    "industries": ["行业名1"]
  },
  "reasoning": "简要说明规划思路（1-2句话）"
}
```

研究类型判断标准：
- 行业分析：关注行业整体发展、市场规模、竞争格局、产业链
- 公司分析：聚焦特定公司的业务、财务、竞争力
- 财务分析：以财务指标分析为核心
- 竞品分析：对比多家公司的产品、市场、财务
- 政策分析：以政策法规解读和影响力评估为主
- 综合研究：包含以上多个维度

图表类型可选：折线图(line)、柱状图(bar)、饼图(pie)、雷达图(radar)、横向柱状图(horizontal_bar)、财务趋势图(financial_trend)

大纲要求：
- 使用"一、二、三..."中文编号
- 8-11个章节
- 第1章为研究摘要，最后1章为结论与建议
- 附录放在最后
- 根据研究类型调整章节内容
"""


class ChiefArchitect:
    """Chief Architect Agent — LLM-powered research strategy planner.

    Uses LLM to:
    1. Understand the research query
    2. Classify research type
    3. Decompose questions
    4. Generate outline
    5. Determine data and chart requirements

    Falls back to rule-based planning if LLM is unavailable.
    """

    name: str = "ChiefArchitect"
    description: str = "规划Agent，基于LLM理解研究任务、分类研究类型、生成研究大纲和检索计划。"

    def __init__(self) -> None:
        self._query_expander = QueryExpansionTool()
        self._llm = get_llm_client()

    async def execute(self, state: ResearchState) -> ResearchState:
        """Execute LLM-powered research planning.

        Args:
            state: Current ResearchState with user_query populated.

        Returns:
            Updated ResearchState with planning fields filled.
        """
        logger.info(f"[{self.name}] Starting LLM research planning for: {state.user_query[:80]}...")
        state.add_log("ChiefArchitect", "execute", "start", {"query": state.user_query[:100]})

        # 1. Generate task_id
        if not state.task_id:
            state.task_id = str(uuid.uuid4())

        # 2. Call LLM for planning
        plan = await self._llm_plan(state.user_query)

        # 3. Populate state from LLM response
        state.research_type = plan.get("research_type", "综合研究")
        state.research_questions = plan.get("research_questions", [])
        state.outline = plan.get("outline", self._default_outline(state.research_type))
        state.data_requirements = plan.get("data_requirements", [])
        state.expected_charts = plan.get("expected_charts", [])

        logger.info(
            f"[{self.name}] LLM classified as: {state.research_type}, "
            f"questions={len(state.research_questions)}, "
            f"outline={len(state.outline)} sections, "
            f"reasoning={plan.get('reasoning', 'N/A')[:80]}"
        )
        state.add_log("ChiefArchitect", "llm_plan", "complete", {
            "research_type": state.research_type,
            "reasoning": plan.get("reasoning", ""),
        })

        # 4. Generate search plan using QueryExpansion tool
        expansion_result = await self._query_expander.run({
            "query": state.user_query,
            "research_type": state.research_type,
            "num_queries": 6,
        })
        if expansion_result["success"]:
            expanded = expansion_result["data"]["expanded_queries"]
            state.search_plan = [
                {"query": eq["query"], "source_type": eq.get("source_type", "news"), "priority": eq.get("priority", 2)}
                for eq in expanded
            ]
        else:
            state.search_plan = [{"query": state.user_query, "source_type": "news", "priority": 1}]

        state.current_step = "ChiefArchitect_complete"
        state.update_timestamp()
        state.add_log("ChiefArchitect", "execute", "complete", {
            "research_type": state.research_type,
            "question_count": len(state.research_questions),
            "outline_sections": len(state.outline),
            "search_queries": len(state.search_plan),
            "expected_charts": state.expected_charts,
        })

        return state

    # ── LLM Planning ──────────────────────────────────────────────────

    async def _llm_plan(self, query: str) -> dict:
        """Call LLM to generate a complete research plan.

        Returns parsed JSON dict. Falls back to defaults on failure.
        """
        messages = [
            {"role": "system", "content": CHIEF_ARCHITECT_SYSTEM},
            {"role": "user", "content": f"请为以下研究任务制定完整的执行计划：\n\n{query}"},
        ]

        try:
            result = await self._llm.chat_json(messages)
            if result.get("_parse_error"):
                logger.warning(f"[{self.name}] LLM JSON parse failed, using fallback. Raw: {str(result.get('raw', ''))[:200]}")
                return self._fallback_plan(query)
            return result
        except Exception as e:
            logger.error(f"[{self.name}] LLM call failed: {e}, using fallback planning")
            return self._fallback_plan(query)

    # ── Fallback (rule-based, used when LLM is unavailable) ────────────

    def _fallback_plan(self, query: str) -> dict:
        """Rule-based fallback when LLM is unavailable."""
        from ..tools.financial_api import FinancialDataAPITool

        # Simple keyword classification
        rtype = "综合研究"
        if any(kw in query for kw in ["行业", "产业", "市场"]):
            rtype = "行业分析"
        if any(kw in query for kw in ["公司", "企业", "集团"]):
            rtype = "公司分析"
        if any(kw in query for kw in ["财务", "营收", "利润", "ROE"]):
            rtype = "财务分析"
        if any(kw in query for kw in ["对比", "竞品", "比较"]):
            rtype = "竞品分析"
        if any(kw in query for kw in ["政策", "法规", "监管"]):
            rtype = "政策分析"

        # Detect entities
        companies = [c for c in FinancialDataAPITool.get_available_companies() if c in query]
        industries = [i for i in FinancialDataAPITool.get_available_industries() if i in query]

        return {
            "research_type": rtype,
            "research_questions": [
                f"{query}的现状和核心特征是什么？",
                f"{query}涉及的关键数据和趋势如何？",
                f"{query}面临的主要挑战和机遇是什么？",
                f"{query}的未来发展方向如何？",
            ],
            "outline": self._default_outline(rtype),
            "data_requirements": [f"{c}财务数据" for c in companies] + [f"{i}行业指标" for i in industries],
            "expected_charts": ["市场规模趋势图（折线图）", "核心指标对比图（柱状图）"],
            "key_entities": {"companies": companies, "industries": industries},
            "reasoning": f"基于规则匹配，判定为{rtype}（LLM不可用时的降级方案）",
        }

    @staticmethod
    def _default_outline(rtype: str) -> list[dict]:
        """Default outline by research type."""
        outlines = {
            "行业分析": [
                {"title": "一、研究摘要", "description": "研究背景、目的和主要发现概述"},
                {"title": "二、行业背景", "description": "行业定义、发展历程、行业分类"},
                {"title": "三、市场规模与发展趋势", "description": "市场规模、增长率、发展趋势"},
                {"title": "四、政策与宏观环境", "description": "相关政策法规、宏观环境影响"},
                {"title": "五、产业链分析", "description": "上下游产业链结构、价值链分析"},
                {"title": "六、竞争格局", "description": "主要企业、市场份额、竞争态势"},
                {"title": "七、核心企业分析", "description": "龙头企业深度分析"},
                {"title": "八、风险因素", "description": "行业面临的主要风险"},
                {"title": "九、未来展望", "description": "行业发展趋势和预测"},
                {"title": "十、结论与建议", "description": "研究结论和投资建议"},
                {"title": "附录：数据来源与参考资料", "description": "引用来源列表"},
            ],
            "公司分析": [
                {"title": "一、研究摘要", "description": "研究背景和主要发现"},
                {"title": "二、公司概况", "description": "公司历史、业务结构、管理层"},
                {"title": "三、财务分析", "description": "营收、利润、毛利率、ROE等"},
                {"title": "四、行业地位", "description": "市场份额、竞争优势、行业排名"},
                {"title": "五、技术与产品", "description": "核心技术、产品矩阵、研发投入"},
                {"title": "六、发展战略", "description": "公司战略规划、未来布局"},
                {"title": "七、风险因素", "description": "经营风险、行业风险、宏观风险"},
                {"title": "八、估值分析", "description": "估值水平、同行业比较"},
                {"title": "九、未来展望", "description": "增长驱动因素、业绩预测"},
                {"title": "十、结论与建议", "description": "研究结论"},
                {"title": "附录：数据来源与参考资料", "description": "引用来源列表"},
            ],
        }
        return outlines.get(rtype, outlines["行业分析"])
