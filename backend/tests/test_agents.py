"""Tests for all 6 agents in the Deep Research Agent Platform."""

import pytest
import sys
sys.path.insert(0, "..")

from app.state.research_state import ResearchState
from app.agents.chief_architect import ChiefArchitect
from app.agents.deep_scout import DeepScout
from app.agents.data_analyst import DataAnalyst
from app.agents.code_wizard import CodeWizard
from app.agents.lead_writer import LeadWriter
from app.agents.critic_master import CriticMaster


# ── Helper ────────────────────────────────────────────────────────────────

def create_state(query: str = "分析中国动力电池行业竞争格局") -> ResearchState:
    """Create a fresh ResearchState for testing."""
    return ResearchState(user_query=query)


# ── ChiefArchitect ────────────────────────────────────────────────────────

class TestChiefArchitect:
    @pytest.mark.asyncio
    async def test_execute_industry_analysis(self):
        agent = ChiefArchitect()
        state = create_state("分析中国动力电池行业竞争格局")
        result = await agent.execute(state)

        assert result.research_type in ["行业分析", "综合研究"]
        assert len(result.research_questions) >= 3
        assert len(result.outline) >= 5
        assert len(result.search_plan) >= 3
        assert len(result.expected_charts) >= 2
        assert len(result.data_requirements) >= 2
        assert len(result.execution_logs) >= 1

    @pytest.mark.asyncio
    async def test_execute_company_analysis(self):
        agent = ChiefArchitect()
        state = create_state("分析宁德时代公司基本面")
        result = await agent.execute(state)

        assert result.research_type in ["公司分析", "综合研究"]
        assert len(result.research_questions) >= 3

    @pytest.mark.asyncio
    async def test_execute_financial_analysis(self):
        agent = ChiefArchitect()
        state = create_state("对比宁德时代和比亚迪的财务表现")
        result = await agent.execute(state)

        assert result.research_type in ["财务分析", "竞品分析", "综合研究"]
        assert len(result.outline) >= 5

    @pytest.mark.asyncio
    async def test_generates_task_id(self):
        agent = ChiefArchitect()
        state = ResearchState(user_query="测试")
        result = await agent.execute(state)
        assert result.task_id != ""


# ── DeepScout ─────────────────────────────────────────────────────────────

class TestDeepScout:
    @pytest.mark.asyncio
    async def test_execute_with_search_plan(self):
        agent = DeepScout()
        state = create_state()
        state.search_plan = [
            {"query": "动力电池 行业规模 2025", "source_type": "industry_report", "priority": 1},
            {"query": "宁德时代 市场份额 动力电池", "source_type": "news", "priority": 1},
        ]
        result = await agent.execute(state)

        assert len(result.raw_search_results) > 0
        assert len(result.filtered_sources) > 0
        assert len(result.evidence_list) > 0
        assert len(result.facts) >= 0
        assert isinstance(result.missing_information, list)

    @pytest.mark.asyncio
    async def test_execute_empty_search_plan(self):
        agent = DeepScout()
        state = create_state()
        result = await agent.execute(state)

        # Should still work with default query
        assert result.current_step == "DeepScout_complete"


# ── DataAnalyst ───────────────────────────────────────────────────────────

class TestDataAnalyst:
    @pytest.mark.asyncio
    async def test_execute_with_battery_query(self):
        agent = DataAnalyst()
        state = create_state("分析动力电池行业竞争格局")
        result = await agent.execute(state)

        assert result.current_step == "DataAnalyst_complete"
        assert "companies" in result.structured_data or "industries" in result.structured_data
        assert isinstance(result.analysis_insights, list)
        assert isinstance(result.chart_requirements, list)


# ── CodeWizard ────────────────────────────────────────────────────────────

class TestCodeWizard:
    @pytest.mark.asyncio
    async def test_execute_with_chart_requirements(self):
        agent = CodeWizard()
        state = create_state()
        state.chart_requirements = [
            {"chart_type": "bar", "title": "营收对比", "description": "测试图表"},
            {"chart_type": "pie", "title": "市场份额", "description": "测试饼图"},
        ]
        # Add some structured data for chart generation
        state.structured_data = {
            "companies": {
                "宁德时代": [
                    {"year": 2025, "revenue": 6200, "net_profit": 750, "gross_margin": 0.29,
                     "roe": 0.252, "market_share": 0.45},
                ],
                "比亚迪": [
                    {"year": 2025, "revenue": 9500, "net_profit": 550, "gross_margin": 0.218,
                     "roe": 0.192, "market_share": 0.29},
                ],
            },
            "industries": {},
        }
        result = await agent.execute(state)

        assert result.current_step == "CodeWizard_complete"
        assert isinstance(result.chart_specs, list)
        assert isinstance(result.visualization_summary, str)

    @pytest.mark.asyncio
    async def test_execute_empty_requirements(self):
        agent = CodeWizard()
        state = create_state()
        result = await agent.execute(state)

        assert result.current_step == "CodeWizard_complete"
        assert result.chart_specs == []


# ── LeadWriter ────────────────────────────────────────────────────────────

class TestLeadWriter:
    @pytest.mark.asyncio
    async def test_execute_full_report(self):
        agent = LeadWriter()
        state = create_state()

        # Setup state with all required data
        state.research_type = "行业分析"
        state.outline = [
            {"title": "一、研究摘要", "description": "概述"},
            {"title": "二、行业背景", "description": "背景"},
            {"title": "六、竞争格局", "description": "竞争"},
            {"title": "八、风险因素", "description": "风险"},
            {"title": "十、结论与建议", "description": "结论"},
            {"title": "附录：数据来源与参考资料", "description": "来源"},
        ]
        state.facts = [
            "2025年动力电池装机量突破800GWh",
            "宁德时代市场份额43.2%",
            "磷酸铁锂占比达67%",
        ]
        state.filtered_sources = [
            {"title": "测试来源", "source": "东方财富", "url": "http://example.com", "publish_time": "2025-06-01"},
        ]
        state.financial_metrics = {
            "宁德时代": {"latest_revenue": 6200, "latest_profit": 750, "latest_margin": 0.29, "latest_roe": 0.252},
        }
        state.structured_data = {
            "companies": {
                "宁德时代": [
                    {"year": 2025, "revenue": 6200, "net_profit": 750, "gross_margin": 0.29,
                     "roe": 0.252, "market_share": 0.45},
                ],
            },
            "industries": {},
        }
        state.analysis_insights = ["营收同比增长22%", "行业CR3达78%"]
        state.chart_specs = [
            {"chart_type": "bar", "title": "营收对比", "description": "Test"},
        ]

        result = await agent.execute(state)

        assert result.draft_report != ""
        assert len(result.draft_report) > 500
        assert len(result.cited_sources) >= 0
        assert len(result.report_versions) == 1


# ── CriticMaster ──────────────────────────────────────────────────────────

class TestCriticMaster:
    @pytest.mark.asyncio
    async def test_execute_review_high_quality(self):
        agent = CriticMaster()
        state = create_state()

        # Build a high-quality report
        state.draft_report = _build_high_quality_report()
        state.facts = [f"Fact {i}" for i in range(15)]
        state.evidence_list = [{"title": f"Source {i}"} for i in range(8)]
        state.filtered_sources = [{"title": f"Source {i}"} for i in range(12)]
        state.outline = [{"title": f"Section {i}"} for i in range(10)]
        state.structured_data = {"companies": {"A": [{"year": 2025, "value": 100}]}}
        state.financial_metrics = {"A": {"rev": 100}}
        state.chart_specs = [{"type": "bar"}]
        state.analysis_insights = ["Insight 1", "Insight 2"]

        result = await agent.execute(state)

        assert "final_score" in result.quality_scores
        assert result.route_decision in ["complete", "revise", "re_research"]
        assert len(result.review_feedback) >= 1

    @pytest.mark.asyncio
    async def test_max_iterations_force_complete(self):
        agent = CriticMaster()
        state = create_state()
        state.draft_report = "Short report."
        state.iteration_count = 3  # Already at max
        state.max_iterations = 3

        result = await agent.execute(state)
        assert result.route_decision == "complete"
        assert "仍需人工复核" in result.draft_report


def _build_high_quality_report() -> str:
    """Build a comprehensive report for testing."""
    sections = []
    sections.append("# 动力电池行业竞争格局分析\n")
    sections.append("## 一、研究摘要\n")
    sections.append("本研究对动力电池行业进行了深入分析。行业规模达18500亿元。\n")
    sections.append("## 二、行业背景\n")
    sections.append("动力电池是新能源汽车的核心部件，中国已成为全球最大生产国。\n")
    sections.append("## 三、市场规模与发展趋势\n")
    sections.append("2025年装机量突破800GWh。因此，行业发展前景广阔。此外，固态电池等新技术不断涌现。\n")
    sections.append("## 六、核心公司/竞品对比\n")
    sections.append("宁德时代营收6200亿元，位列第一。比亚迪、亿纬锂能等紧随其后。\n")
    sections.append("## 八、风险因素\n")
    sections.append("- 原材料价格波动风险\n- 产能过剩风险\n")
    sections.append("## 十、结论与建议\n")
    sections.append("综上所述，动力电池行业具有较高投资价值。建议关注龙头企业。\n")
    sections.append("## 附录：数据来源与参考资料\n")
    sections.append("- 东方财富证券研究\n")
    return "\n".join(sections)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
