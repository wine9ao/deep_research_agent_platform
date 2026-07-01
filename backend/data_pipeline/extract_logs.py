"""Extract structured training samples from agent execution logs.

Reads execution_logs from completed research tasks and extracts
function-call training samples with the following structure:
- task: user's research question
- context: current research context
- agent: which agent was executing
- available_tools: tools available to the agent
- expected_tool: the correct tool to use
- arguments: tool arguments
- label: success/failure reason
- route_type: the routing type
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def extract_from_logs(logs: list[dict], task_info: dict) -> list[dict]:
    """Extract training samples from execution logs.

    Args:
        logs: List of execution log entries.
        task_info: Dict with task metadata (query, research_type, etc.).

    Returns:
        List of training sample dicts.
    """
    samples: list[dict] = []

    for entry in logs:
        agent = entry.get("agent", "")
        action = entry.get("action", "")
        details = entry.get("details", {})

        # Determine available tools for each agent
        agent_tools = _get_agent_tools(agent)

        # Build context from previous logs
        context = _build_context(logs, entry)

        sample = {
            "task": task_info.get("query", ""),
            "context": context,
            "agent": agent,
            "available_tools": agent_tools,
            "expected_tool": _infer_tool(agent, action, details),
            "arguments": _infer_arguments(agent, action, details),
            "label": _infer_label(entry),
            "route_type": task_info.get("research_type", "research"),
            "reason": _infer_reason(agent, action, details),
        }

        if sample["expected_tool"]:
            samples.append(sample)

    return samples


def _get_agent_tools(agent: str) -> list[str]:
    """Get the list of tools available to each agent."""
    tool_map = {
        "ChiefArchitect": ["QueryExpansionTool"],
        "DeepScout": ["WebSearchTool", "LocalKnowledgeBaseTool", "BM25SearchTool", "VectorSearchTool"],
        "DataAnalyst": ["FinancialDataAPITool", "Text2SQLTool", "DataAnalysisTool"],
        "CodeWizard": ["PythonExecutionTool", "ChartGenerationTool", "EChartsSpecTool"],
        "LeadWriter": ["ReportExportTool"],
        "CriticMaster": [],
    }
    return tool_map.get(agent, [])


def _build_context(logs: list[dict], current_entry: dict) -> str:
    """Build a context string from preceding logs."""
    current_idx = logs.index(current_entry) if current_entry in logs else -1
    prev_entries = logs[max(0, current_idx - 3):current_idx] if current_idx > 0 else []
    context_parts = []
    for e in prev_entries:
        context_parts.append(f"[{e.get('agent', '')}] {e.get('action', '')}: {str(e.get('details', {}))[:100]}")
    return " | ".join(context_parts) if context_parts else "开始研究任务"


def _infer_tool(agent: str, action: str, details: dict) -> str:
    """Infer which tool was (or should have been) used."""
    if "search" in action.lower() or "query" in action.lower():
        return "WebSearchTool"
    if "query_expansion" in action.lower() or "expand" in action.lower():
        return "QueryExpansionTool"
    if "kb" in action.lower() or "knowledge" in action.lower():
        return "LocalKnowledgeBaseTool"
    if "financial" in action.lower() or "company" in action.lower():
        return "FinancialDataAPITool"
    if "sql" in action.lower():
        return "Text2SQLTool"
    if "analysis" in action.lower() or "analyze" in action.lower():
        return "DataAnalysisTool"
    if "chart" in action.lower() or "generate_chart" in action.lower():
        return "ChartGenerationTool"
    if "python" in action.lower() or "execute" in action.lower():
        return "PythonExecutionTool"
    if "export" in action.lower() or "report" in action.lower():
        return "ReportExportTool"
    return ""


def _infer_arguments(agent: str, action: str, details: dict) -> dict:
    """Infer tool arguments from the log details."""
    if "query" in details:
        return {"query": str(details["query"])[:200], "top_k": 5}
    if "source_type" in details:
        return {"query": str(details.get("query", "")), "source_type": str(details["source_type"])}
    return {"query": str(details)[:200]}


def _infer_label(entry: dict) -> str:
    """Infer the success/failure label from the log entry."""
    action = entry.get("action", "")
    details = entry.get("details", {})

    if "error" in action.lower():
        return "chain_break"
    if "missing" in str(details).lower():
        return "missing_params"
    if "unsafe" in str(details).lower():
        return "unsafe_sql"
    if "low_relevance" in str(details).lower():
        return "low_relevance"
    if "wrong" in str(details).lower():
        return "wrong_tool"
    if "misroute" in str(details).lower():
        return "misroute"
    return "success"


def _infer_reason(agent: str, action: str, details: dict) -> str:
    """Infer the reason/rationale for the tool choice."""
    reason_map = {
        "ChiefArchitect": "需要规划研究任务和拆解问题",
        "DeepScout": "需要检索行业公开信息",
        "DataAnalyst": "需要查询财务和行业数据进行分析",
        "CodeWizard": "需要生成数据可视化图表",
        "LeadWriter": "需要导出最终研究报告",
        "CriticMaster": "需要评估报告质量",
    }
    if action == "search":
        return "需要执行信息检索获取最新数据"
    if action == "query_expansion":
        return "需要将研究问题拆解为多个检索查询"
    return reason_map.get(agent, "执行研究任务")


def main() -> None:
    """Extract training samples from log files."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract FunctionCall training data from execution logs")
    parser.add_argument("--input", "-i", help="Input log JSON file path")
    parser.add_argument("--output", "-o", default="seed_samples.json", help="Output JSON file path")
    args = parser.parse_args()

    # Load logs
    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
            logs = data.get("logs", [])
            task_info = {"query": data.get("query", ""), "research_type": data.get("research_type", "")}
    else:
        print("No input file provided. Generating mock seed data...")
        logs, task_info = _generate_mock_logs()

    # Extract samples
    samples = extract_from_logs(logs, task_info)
    print(f"Extracted {len(samples)} training samples")

    # Save
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)
    print(f"Saved to {args.output}")


def _generate_mock_logs() -> tuple[list[dict], dict]:
    """Generate mock execution logs for testing."""
    task_info = {
        "query": "分析中国动力电池行业竞争格局",
        "research_type": "行业分析",
    }

    logs = [
        {"agent": "ChiefArchitect", "action": "classify", "timestamp": "2025-07-01T10:00:00", "details": {"research_type": "行业分析"}},
        {"agent": "ChiefArchitect", "action": "expand_query", "timestamp": "2025-07-01T10:00:01", "details": {"query": "动力电池 行业规模 2025"}},
        {"agent": "DeepScout", "action": "search", "timestamp": "2025-07-01T10:00:02", "details": {"query": "动力电池 行业规模 市场份额 2025", "top_k": 5}},
        {"agent": "DeepScout", "action": "reflection", "timestamp": "2025-07-01T10:00:03", "details": {"missing_information": "政策信息不足"}},
        {"agent": "DataAnalyst", "action": "query_financial", "timestamp": "2025-07-01T10:00:04", "details": {"company_names": ["宁德时代", "比亚迪"]}},
        {"agent": "DataAnalyst", "action": "text2sql", "timestamp": "2025-07-01T10:00:05", "details": {"question": "查询宁德时代近三年营收"}},
        {"agent": "CodeWizard", "action": "generate_chart", "timestamp": "2025-07-01T10:00:06", "details": {"chart_type": "bar", "title": "营收对比"}},
        {"agent": "LeadWriter", "action": "generate_report", "timestamp": "2025-07-01T10:00:07", "details": {"sections": 11}},
        {"agent": "CriticMaster", "action": "review", "timestamp": "2025-07-01T10:00:08", "details": {"final_score": 88}},
        {"agent": "DeepScout", "action": "search_missing", "timestamp": "2025-07-01T10:00:09", "details": {"reason": "信息不足"}},
    ]

    return logs, task_info


if __name__ == "__main__":
    main()
