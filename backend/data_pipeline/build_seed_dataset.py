"""Build a seed dataset of 3,030 FunctionCall training samples.

Generates mock training samples covering:
- 6 agent types
- 9 tools
- Multiple research domains (动力电池, AI算力, 低空经济, etc.)
- Both success and failure cases (6 failure types)
"""

from __future__ import annotations

import json
import os
import random
from typing import Any

# ── Seed data templates ───────────────────────────────────────────────────

_SEED_TASKS = [
    "分析中国动力电池行业竞争格局",
    "生成一份宁德时代公司基本面与行业地位研究报告",
    "分析AI算力产业链未来三年的投资机会",
    "对比贵州茅台、五粮液和泸州老窖的财务表现与行业竞争力",
    "分析低空经济行业政策、市场规模、核心公司与风险因素",
    "研究中国光伏产业现状及未来发展趋势",
    "分析新能源汽车行业竞争格局与投资机会",
    "研究中国白酒行业渠道变革与消费趋势",
    "分析动力电池回收行业市场前景",
    "研究半导体产业链国产替代进程",
    "分析中国医疗器械行业竞争格局",
    "研究人工智能大模型产业应用前景",
    "分析中国海上风电行业投资机会",
    "研究储能行业技术路线与市场前景",
    "分析中国创新药研发趋势与竞争格局",
]

_SEED_RESEARCH_TYPES = ["行业分析", "公司分析", "财务分析", "竞品分析", "政策分析", "综合研究"]

_AGENT_TOOLS = {
    "ChiefArchitect": ["QueryExpansionTool"],
    "DeepScout": ["WebSearchTool", "LocalKnowledgeBaseTool", "BM25SearchTool", "VectorSearchTool"],
    "DataAnalyst": ["FinancialDataAPITool", "Text2SQLTool", "DataAnalysisTool"],
    "CodeWizard": ["PythonExecutionTool", "ChartGenerationTool", "EChartsSpecTool"],
    "LeadWriter": ["ReportExportTool"],
    "CriticMaster": [],
}

_TOOL_ARGUMENTS = {
    "QueryExpansionTool": [
        {"query": "动力电池 行业规模 2025", "num_queries": 6},
        {"query": "宁德时代 财务数据 营收", "num_queries": 5},
        {"query": "AI算力 产业链 投资", "num_queries": 5},
    ],
    "WebSearchTool": [
        {"query": "动力电池 行业规模 市场份额 2025", "top_k": 5, "recency_days": 180},
        {"query": "宁德时代 年报 2024 净利润", "top_k": 5, "source_type": "financial"},
        {"query": "低空经济 政策 市场规模 eVTOL", "top_k": 5, "recency_days": 365},
    ],
    "FinancialDataAPITool": [
        {"query_type": "company", "company_names": ["宁德时代", "比亚迪"], "years": [2022, 2023, 2024, 2025]},
        {"query_type": "industry", "industry_names": ["动力电池"]},
    ],
    "Text2SQLTool": [
        {"question": "查询宁德时代近三年营收和净利润"},
        {"question": "对比比亚迪和宁德时代2024年毛利率"},
    ],
    "DataAnalysisTool": [
        {"operation": "yoy_growth", "data": [], "value_column": "revenue", "group_column": "company_name"},
        {"operation": "cagr", "data": [], "value_column": "market_size", "group_column": "industry_name"},
    ],
    "ChartGenerationTool": [
        {"chart_type": "bar", "title": "2025年核心企业营收对比", "labels": ["宁德时代", "比亚迪", "亿纬锂能"]},
        {"chart_type": "pie", "title": "动力电池市场份额分布", "labels": ["宁德时代", "比亚迪", "其他"]},
    ],
    "PythonExecutionTool": [
        {"code": "import pandas as pd\nimport numpy as np\ndata = pd.DataFrame({'a': [1,2,3]})\nprint(data.describe())"},
    ],
    "LocalKnowledgeBaseTool": [
        {"action": "search", "query": "动力电池 产业链", "top_k": 5, "method": "hybrid"},
    ],
    "ReportExportTool": [
        {"action": "export_both", "content": "# 研究报告\n...", "title": "动力电池行业分析报告"},
    ],
}

_FAILURE_TYPES = {
    "misroute": {"label": "misroute", "reason": "路由错误：应使用WebSearchTool但错误调用了FinancialDataAPITool"},
    "wrong_tool": {"label": "wrong_tool", "reason": "工具选择错误：应使用DataAnalysisTool但调用了ChartGenerationTool"},
    "missing_params": {"label": "missing_params", "reason": "参数缺失：缺少必需的query参数"},
    "chain_break": {"label": "chain_break", "reason": "链式断裂：上一步输出格式不符合下一步输入要求"},
    "unsafe_sql": {"label": "unsafe_sql", "reason": "SQL不安全：生成的SQL包含DELETE语句"},
    "low_relevance": {"label": "low_relevance", "reason": "检索结果与问题相关性低，需要调整检索策略"},
}


def build_seed_dataset(output_path: str = "seed_dataset.json", target_count: int = 3030) -> list[dict]:
    """Generate a seed dataset of FunctionCall training samples.

    Args:
        output_path: Path to save the dataset.
        target_count: Target number of samples (default 3030).

    Returns:
        List of training sample dicts.
    """
    random.seed(42)
    samples: list[dict] = []
    sample_id = 0

    while len(samples) < target_count:
        task = random.choice(_SEED_TASKS)
        agent = random.choice(list(_AGENT_TOOLS.keys()))
        tools = _AGENT_TOOLS[agent]

        if not tools:
            continue

        expected_tool = random.choice(tools)
        arguments = random.choice(_TOOL_ARGUMENTS.get(expected_tool, [{}]))

        # ~80% success, ~20% failure
        is_failure = random.random() < 0.20
        label = "success"
        reason = ""

        if is_failure:
            failure_type = random.choice(list(_FAILURE_TYPES.keys()))
            failure_info = _FAILURE_TYPES[failure_type]
            label = failure_info["label"]
            reason = failure_info["reason"]
        else:
            reason = f"该任务需要{expected_tool}来完成{agent}的核心职能"

        sample = {
            "id": f"seed_{sample_id:06d}",
            "task": task,
            "context": f"用户需要{random.choice(_SEED_RESEARCH_TYPES)}，agent={agent}，当前步骤需要调用合适的工具",
            "agent": agent,
            "available_tools": tools,
            "expected_tool": expected_tool,
            "arguments": arguments,
            "label": label,
            "route_type": random.choice(_SEED_RESEARCH_TYPES),
            "reason": reason,
        }

        samples.append(sample)
        sample_id += 1

        # Add variations: same task, different agents
        if sample_id < target_count and random.random() < 0.5:
            agent2 = random.choice([a for a in _AGENT_TOOLS if a != agent and _AGENT_TOOLS[a]])
            tools2 = _AGENT_TOOLS[agent2]
            expected_tool2 = random.choice(tools2)
            arguments2 = random.choice(_TOOL_ARGUMENTS.get(expected_tool2, [{}]))

            samples.append({
                "id": f"seed_{sample_id:06d}",
                "task": task,
                "context": f"用户需要{random.choice(_SEED_RESEARCH_TYPES)}，agent={agent2}，当前步骤需要调用合适的工具",
                "agent": agent2,
                "available_tools": tools2,
                "expected_tool": expected_tool2,
                "arguments": arguments2,
                "label": "success",
                "route_type": random.choice(_SEED_RESEARCH_TYPES),
                "reason": f"该任务需要{expected_tool2}来完成{agent2}的核心职能",
            })
            sample_id += 1

    # Save
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    print(f"Built seed dataset: {len(samples)} samples → {output_path}")
    return samples


if __name__ == "__main__":
    build_seed_dataset()
