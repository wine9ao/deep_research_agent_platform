"""Query Expansion Tool — decomposes research questions into multiple search queries."""

from __future__ import annotations

import re
from typing import Any

from .base import BaseTool

# ── Expansion templates by research type ──────────────────────────────────

_EXPANSION_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "行业分析": [
        {"suffix": "行业规模 市场规模 {year}", "source_type": "industry_report", "priority": 1},
        {"suffix": "行业政策 监管 法规", "source_type": "policy", "priority": 1},
        {"suffix": "产业链 上下游 供应链", "source_type": "industry_report", "priority": 2},
        {"suffix": "行业竞争格局 市场份额", "source_type": "news", "priority": 1},
        {"suffix": "行业发展趋势 未来展望", "source_type": "industry_report", "priority": 2},
        {"suffix": "行业风险 挑战", "source_type": "analysis", "priority": 3},
        {"suffix": "技术路线 创新", "source_type": "tech", "priority": 2},
    ],
    "公司分析": [
        {"suffix": "公司概况 业务结构 管理层", "source_type": "company_info", "priority": 1},
        {"suffix": "财务数据 营收 净利润", "source_type": "financial", "priority": 1},
        {"suffix": "行业地位 市场份额 竞争优势", "source_type": "analysis", "priority": 1},
        {"suffix": "发展战略 未来规划", "source_type": "news", "priority": 2},
        {"suffix": "风险因素 挑战", "source_type": "analysis", "priority": 3},
        {"suffix": "最新动态 公告 新闻", "source_type": "news", "priority": 2},
    ],
    "财务分析": [
        {"suffix": "营收 净利润 同比增长 {year}", "source_type": "financial", "priority": 1},
        {"suffix": "毛利率 净利率 ROE", "source_type": "financial", "priority": 1},
        {"suffix": "资产负债率 现金流", "source_type": "financial", "priority": 2},
        {"suffix": "估值 PE PB PS", "source_type": "financial", "priority": 2},
        {"suffix": "财务风险 债务", "source_type": "analysis", "priority": 3},
    ],
    "竞品分析": [
        {"suffix": "对比 财务 市场份额", "source_type": "financial", "priority": 1},
        {"suffix": "产品对比 技术对比", "source_type": "tech", "priority": 1},
        {"suffix": "竞争优势 劣势 SWOT", "source_type": "analysis", "priority": 2},
        {"suffix": "定价策略 渠道对比", "source_type": "analysis", "priority": 3},
        {"suffix": "用户评价 口碑对比", "source_type": "news", "priority": 3},
    ],
    "政策分析": [
        {"suffix": "政策文件 法律法规", "source_type": "policy", "priority": 1},
        {"suffix": "政策影响 行业影响", "source_type": "analysis", "priority": 1},
        {"suffix": "地方政策 补贴 扶持", "source_type": "policy", "priority": 2},
        {"suffix": "国际对比 国外政策", "source_type": "policy", "priority": 2},
        {"suffix": "政策趋势 未来方向", "source_type": "analysis", "priority": 3},
    ],
    "综合研究": [
        {"suffix": "行业规模 市场规模 {year}", "source_type": "industry_report", "priority": 1},
        {"suffix": "政策环境 监管", "source_type": "policy", "priority": 1},
        {"suffix": "核心企业 竞争格局", "source_type": "analysis", "priority": 1},
        {"suffix": "财务数据 营收", "source_type": "financial", "priority": 2},
        {"suffix": "发展趋势 未来展望", "source_type": "industry_report", "priority": 2},
        {"suffix": "风险因素 挑战", "source_type": "analysis", "priority": 3},
        {"suffix": "投资机会 建议", "source_type": "analysis", "priority": 2},
    ],
}

# ── Keyword extraction patterns ───────────────────────────────────────────

_KEYWORD_PATTERNS = [
    (r"动力电池", ["动力电池", "锂电池", "磷酸铁锂", "三元锂电池"]),
    (r"新能源汽车?", ["新能源汽车", "电动车", "新能源车"]),
    (r"AI算力|人工智能算力", ["AI算力", "GPU", "算力芯片"]),
    (r"低空经济", ["低空经济", "eVTOL", "无人机"]),
    (r"白酒", ["白酒", "高端白酒", "酱香型"]),
    (r"光伏", ["光伏", "太阳能", "光伏组件"]),
    (r"宁德时代|CATL", ["宁德时代", "CATL"]),
    (r"比亚迪", ["比亚迪", "BYD"]),
    (r"亿纬锂能", ["亿纬锂能"]),
    (r"国轩高科", ["国轩高科"]),
    (r"中创新航", ["中创新航"]),
    (r"贵州茅台", ["贵州茅台"]),
    (r"五粮液", ["五粮液"]),
    (r"泸州老窖", ["泸州老窖"]),
]

# ── Company-specific expansions ───────────────────────────────────────────

_COMPANY_SPECIFIC: dict[str, list[str]] = {
    "宁德时代": [
        "宁德时代 营收 净利润 2024 2025",
        "宁德时代 市场份额 动力电池",
        "宁德时代 产能 海外布局",
        "宁德时代 技术路线 麒麟电池",
    ],
    "比亚迪": [
        "比亚迪 营收 净利润 2024 2025",
        "比亚迪 新能源汽车 销量",
        "比亚迪 刀片电池 技术",
        "比亚迪 海外市场 出口",
    ],
}


class QueryExpansionTool(BaseTool):
    """Decompose a research question into multiple targeted search queries.

    Uses keyword matching and template-based expansion to generate
    a diverse set of search queries covering different aspects of
    the research topic.
    """

    name: str = "query_expansion"
    description: str = (
        "将研究问题拆解为多个精准的检索查询，"
        "支持行业分析、公司分析、财务分析、竞品分析、政策分析等研究类型。"
    )

    def __init__(self) -> None:
        self._current_year = "2025"

    async def run(self, input: dict) -> dict:
        """Expand a research query into multiple search queries.

        Args:
            input: dict with keys:
                - query (str): The research question
                - research_type (str, optional): One of the research types
                - num_queries (int, optional): Max queries to generate (default 6)

        Returns:
            dict with success and data containing list of query objects
        """
        try:
            query = input.get("query", "")
            research_type = input.get("research_type", "综合研究")
            num_queries = input.get("num_queries", 6)

            if not query:
                return {"success": False, "data": None, "error": "query is required"}

            expanded = self._expand(query, research_type, num_queries)

            return {
                "success": True,
                "data": {
                    "original_query": query,
                    "research_type": research_type,
                    "expanded_queries": expanded,
                    "count": len(expanded),
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _expand(self, query: str, research_type: str, num_queries: int) -> list[dict]:
        """Core expansion logic."""
        templates = _EXPANSION_TEMPLATES.get(research_type, _EXPANSION_TEMPLATES["综合研究"])
        expanded: list[dict] = []

        # Detect domain keywords
        domain_keywords: list[str] = []
        for pattern, keywords in _KEYWORD_PATTERNS:
            if re.search(pattern, query):
                domain_keywords.extend(keywords)
                break

        # Detect specific companies
        companies: list[str] = []
        for company in _COMPANY_SPECIFIC:
            if company in query:
                companies.append(company)

        # Generate from templates
        for i, tmpl in enumerate(templates):
            if len(expanded) >= num_queries:
                break
            suffix = tmpl["suffix"].replace("{year}", self._current_year)
            expanded.append({
                "query": f"{query} {suffix}",
                "source_type": tmpl["source_type"],
                "priority": tmpl["priority"],
                "index": i,
            })

        # Add domain-specific queries
        for kw in domain_keywords[:3]:
            if len(expanded) >= num_queries:
                break
            expanded.append({
                "query": f"{kw} 行业报告 2025",
                "source_type": "industry_report",
                "priority": 1,
                "index": len(expanded),
            })

        # Add company-specific queries if detected
        for company in companies:
            specific_queries = _COMPANY_SPECIFIC.get(company, [])
            for sq in specific_queries:
                if len(expanded) >= num_queries:
                    break
                expanded.append({
                    "query": sq,
                    "source_type": "financial",
                    "priority": 1,
                    "index": len(expanded),
                })

        return expanded[:num_queries]
