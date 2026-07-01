"""Tests for all tools in the Deep Research Agent Platform."""

import pytest
import asyncio

# Import tools
import sys
sys.path.insert(0, "..")

from app.tools.base import BaseTool
from app.tools.web_search import WebSearchTool
from app.tools.query_expansion import QueryExpansionTool
from app.tools.financial_api import FinancialDataAPITool
from app.tools.text2sql import Text2SQLTool, validate_sql_safety
from app.tools.data_analysis import DataAnalysisTool
from app.tools.chart_generation import ChartGenerationTool
from app.tools.python_execution import PythonExecutionTool, check_python_code_safety
from app.tools.report_export import ReportExportTool


# ── BaseTool ──────────────────────────────────────────────────────────────

class TestBaseTool:
    def test_base_tool_abstract(self):
        """BaseTool should be abstract and have name/description."""
        assert BaseTool.name == "base_tool"
        assert BaseTool.description == "Base tool description"

    def test_to_dict(self):
        """to_dict should return name and description."""

        class TestTool(BaseTool):
            name = "test"
            description = "test desc"

            async def run(self, input: dict) -> dict:
                return {"success": True, "data": None, "error": None}

        tool = TestTool()
        d = tool.to_dict()
        assert d == {"name": "test", "description": "test desc"}


# ── WebSearchTool ─────────────────────────────────────────────────────────

class TestWebSearchTool:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        tool = WebSearchTool()
        result = await tool.run({"query": "动力电池 行业"})
        assert result["success"]
        assert len(result["data"]["results"]) > 0
        assert "title" in result["data"]["results"][0]

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self):
        tool = WebSearchTool()
        result = await tool.run({"query": ""})
        assert not result["success"]

    @pytest.mark.asyncio
    async def test_search_recency_filter(self):
        tool = WebSearchTool()
        result = await tool.run({"query": "动力电池", "recency_days": 30})
        assert result["success"]


# ── QueryExpansionTool ────────────────────────────────────────────────────

class TestQueryExpansionTool:
    @pytest.mark.asyncio
    async def test_expand_battery_query(self):
        tool = QueryExpansionTool()
        result = await tool.run({"query": "分析动力电池行业竞争格局", "research_type": "行业分析"})
        assert result["success"]
        assert len(result["data"]["expanded_queries"]) >= 3

    @pytest.mark.asyncio
    async def test_expand_company_query(self):
        tool = QueryExpansionTool()
        result = await tool.run({"query": "宁德时代公司分析", "research_type": "公司分析"})
        assert result["success"]


# ── FinancialDataAPITool ──────────────────────────────────────────────────

class TestFinancialDataAPITool:
    @pytest.mark.asyncio
    async def test_query_company(self):
        tool = FinancialDataAPITool()
        result = await tool.run({"query_type": "company", "company_names": ["宁德时代"]})
        assert result["success"]
        assert "宁德时代" in result["data"]
        assert len(result["data"]["宁德时代"]) == 4  # 2022-2025

    @pytest.mark.asyncio
    async def test_query_industry(self):
        tool = FinancialDataAPITool()
        result = await tool.run({"query_type": "industry", "industry_names": ["动力电池"]})
        assert result["success"]
        assert "动力电池" in result["data"]

    def test_available_companies(self):
        companies = FinancialDataAPITool.get_available_companies()
        assert "宁德时代" in companies
        assert "比亚迪" in companies
        assert len(companies) == 5

    def test_available_industries(self):
        industries = FinancialDataAPITool.get_available_industries()
        assert "动力电池" in industries
        assert len(industries) == 6


# ── Text2SQLTool ──────────────────────────────────────────────────────────

class TestText2SQLTool:
    def test_safe_select(self):
        is_safe, reason = validate_sql_safety("SELECT * FROM companies")
        assert is_safe

    def test_unsafe_delete(self):
        is_safe, reason = validate_sql_safety("DELETE FROM companies WHERE id=1")
        assert not is_safe

    def test_unsafe_update(self):
        is_safe, reason = validate_sql_safety("UPDATE companies SET name='test'")
        assert not is_safe

    def test_unsafe_drop(self):
        is_safe, reason = validate_sql_safety("DROP TABLE companies")
        assert not is_safe

    def test_not_starting_with_select(self):
        is_safe, reason = validate_sql_safety("INSERT INTO companies VALUES (1)")
        assert not is_safe

    @pytest.mark.asyncio
    async def test_question_to_sql(self):
        tool = Text2SQLTool(db_path=":memory:")
        result = await tool.run({"question": "查询宁德时代近三年营收和净利润"})
        # May fail due to no DB initialized, but should not crash
        assert "sql" in result or "error" in result


# ── DataAnalysisTool ──────────────────────────────────────────────────────

class TestDataAnalysisTool:
    @pytest.mark.asyncio
    async def test_summary_stats(self):
        tool = DataAnalysisTool()
        data = [
            {"name": "A", "value": 10},
            {"name": "B", "value": 20},
            {"name": "C", "value": 30},
        ]
        result = await tool.run({"operation": "summary_stats", "data": data, "value_column": "value"})
        assert result["success"]
        assert "insights" in result["data"]
        assert len(result["data"]["insights"]) >= 2

    @pytest.mark.asyncio
    async def test_ranking(self):
        tool = DataAnalysisTool()
        data = [
            {"company": "A", "score": 80},
            {"company": "B", "score": 95},
            {"company": "C", "score": 70},
        ]
        result = await tool.run({
            "operation": "ranking",
            "data": data,
            "value_column": "score",
            "group_column": "company",
        })
        assert result["success"]
        assert result["data"]["table"][0]["排名"] == 1

    @pytest.mark.asyncio
    async def test_empty_data(self):
        tool = DataAnalysisTool()
        result = await tool.run({"operation": "summary_stats", "data": [], "value_column": "x"})
        assert not result["success"]


# ── ChartGenerationTool ───────────────────────────────────────────────────

class TestChartGenerationTool:
    @pytest.mark.asyncio
    async def test_generate_bar_chart(self):
        tool = ChartGenerationTool()
        result = await tool.run({
            "chart_type": "bar",
            "title": "测试图表",
            "labels": ["A", "B", "C"],
            "series_data": [{"name": "系列1", "data": [10, 20, 30]}],
        })
        assert result["success"]
        assert "echarts_option" in result["data"]
        assert "xAxis" in result["data"]["echarts_option"]

    @pytest.mark.asyncio
    async def test_generate_pie_chart(self):
        tool = ChartGenerationTool()
        result = await tool.run({
            "chart_type": "pie",
            "title": "测试饼图",
            "series_data": [{"name": "A", "value": 40}, {"name": "B", "value": 60}],
        })
        assert result["success"]

    @pytest.mark.asyncio
    async def test_unsupported_chart_type(self):
        tool = ChartGenerationTool()
        result = await tool.run({"chart_type": "unknown", "title": "Test"})
        assert not result["success"]


# ── PythonExecutionTool ───────────────────────────────────────────────────

class TestPythonExecutionTool:
    def test_safe_code(self):
        is_safe, reason = check_python_code_safety("print('hello')\nx = 1 + 2")
        assert is_safe

    def test_unsafe_os_import(self):
        is_safe, reason = check_python_code_safety("import os\nos.system('ls')")
        assert not is_safe

    def test_unsafe_eval(self):
        is_safe, reason = check_python_code_safety("eval('1+1')")
        assert not is_safe

    def test_unsafe_subprocess(self):
        is_safe, reason = check_python_code_safety("import subprocess\nsubprocess.run('ls')")
        assert not is_safe

    @pytest.mark.asyncio
    async def test_execute_safe_code(self):
        tool = PythonExecutionTool()
        result = await tool.run({"code": "x = sum([1, 2, 3])\nprint(f'Sum: {x}')"})
        assert result["success"]
        assert "Sum: 6" in result["data"]["stdout"]

    @pytest.mark.asyncio
    async def test_execute_unsafe_code(self):
        tool = PythonExecutionTool()
        result = await tool.run({"code": "import os\nos.system('ls')"})
        assert not result["success"]


# ── ReportExportTool ──────────────────────────────────────────────────────

class TestReportExportTool:
    @pytest.mark.asyncio
    async def test_export_markdown(self):
        tool = ReportExportTool(export_dir="/tmp/test_exports")
        result = await tool.run({
            "action": "export_md",
            "content": "# Test Report\n\nHello world.",
            "filename": "test_report",
        })
        assert result["success"]
        assert result["data"]["files"]["md"].endswith(".md")

    @pytest.mark.asyncio
    async def test_export_empty_content(self):
        tool = ReportExportTool()
        result = await tool.run({"action": "export_md", "content": ""})
        assert not result["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
