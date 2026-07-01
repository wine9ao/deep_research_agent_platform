"""CriticMaster Agent — LLM-powered quality review and routing."""

from __future__ import annotations

from typing import Any

from ..llm.client import get_llm_client
from ..state.research_state import ResearchState
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── LLM prompt ────────────────────────────────────────────────────────────

CRITIC_SYSTEM = """你是一名资深研究报告质量评审专家（Critic Master）。对研究报告进行多维度质量评审。

## 评审维度

1. **完整性 (completeness)**：是否覆盖了大纲中的所有章节？每章内容是否充实？
2. **事实准确性 (factuality)**：数据和事实是否有来源支撑？是否存在编造或幻觉？
3. **逻辑性 (logic)**：章节之间的逻辑是否连贯？论证过程是否合理？
4. **引用质量 (citation)**：是否标注了数据来源？引用是否充分？
5. **数据充分性 (data)**：数据分析是否充分？定量分析占比是否足够？
6. **可读性 (readability)**：报告是否易于阅读？结构和排版是否合理？

## 评分标准

每项0-100分：
- 90-100：优秀，该维度表现突出
- 80-89：良好，基本达标
- 70-79：一般，有待改进
- 60-69：不足，需要修改
- 60以下：严重不足

## 路由决策

- final_score >= 85 → "complete"（质量达标，可以结束）
- factuality < 75 或 data < 75 → "re_research"（信息不足，需要回到检索阶段）
- readability < 75 或 logic < 75 → "revise"（需要修改报告文本）
- 其他情况 → 根据综合判断决定

## 输出格式

严格返回JSON：
```json
{
  "scores": {
    "completeness_score": 85,
    "factuality_score": 80,
    "logic_score": 82,
    "citation_score": 78,
    "data_score": 83,
    "readability_score": 88,
    "final_score": 83
  },
  "feedback": ["具体反馈1", "具体反馈2"],
  "decision": "revise",
  "hallucination_risk": "发现的幻觉风险或空字符串",
  "over_inference": "发现的过度推断或空字符串",
  "summary": "评审总结（1-2句话）"
}
```
"""


class CriticMaster:
    """Critic Master Agent — LLM-powered quality review.

    Uses LLM for:
    - Multi-dimensional quality scoring
    - Hallucination and over-inference detection
    - Specific feedback generation
    - Routing decision

    Falls back to rule-based scoring if LLM is unavailable.
    """

    name: str = "CriticMaster"
    description: str = "质量评审Agent，使用LLM进行7维度质量评分和智能路由决策。"

    ROUTE_COMPLETE = "complete"
    ROUTE_RE_RESEARCH = "re_research"
    ROUTE_REVISE = "revise"

    def __init__(self) -> None:
        self._llm = get_llm_client()

    async def execute(self, state: ResearchState) -> ResearchState:
        """Execute LLM-powered quality review.

        Args:
            state: ResearchState with draft_report.

        Returns:
            Updated ResearchState with quality_scores, review_feedback, route_decision.
        """
        logger.info(f"[{self.name}] Starting LLM quality review (iteration {state.iteration_count + 1}/{state.max_iterations})...")
        state.add_log("CriticMaster", "execute", "start", {"iteration": state.iteration_count + 1})

        report = state.draft_report
        if not report:
            state.add_error("CriticMaster: No draft report to review")
            state.route_decision = self.ROUTE_RE_RESEARCH
            return state

        # ── LLM review ───────────────────────────────────────────────
        review = await self._llm_review(state, report)

        scores = review.get("scores", {})
        feedback = review.get("feedback", [])
        decision = review.get("decision", self.ROUTE_COMPLETE)
        hallucination_risk = review.get("hallucination_risk", "")
        over_inference = review.get("over_inference", "")

        # ── Enforce max iterations ────────────────────────────────────
        if state.iteration_count >= state.max_iterations:
            logger.warning(f"[{self.name}] Max iterations ({state.max_iterations}) reached. Forcing complete.")
            decision = self.ROUTE_COMPLETE
            if "仍需人工复核" not in state.draft_report:
                state.draft_report += (
                    f"\n\n---\n> ⚠️ **提示**：本研究已达到最大迭代次数限制（{state.max_iterations}次），"
                    "部分内容可能需要人工复核。建议在关键数据和结论方面进行进一步验证。\n"
                )

        # ── Ensure final_score exists ────────────────────────────────
        if "final_score" not in scores:
            scores["final_score"] = self._calc_fallback_final(scores)

        # ── Store results ────────────────────────────────────────────
        state.quality_scores = scores
        state.route_decision = decision
        state.review_feedback.append({
            "iteration": state.iteration_count + 1,
            "scores": scores,
            "feedback": feedback,
            "decision": decision,
            "timestamp": state.updated_at,
            "hallucination_risk": hallucination_risk,
            "over_inference": over_inference,
            "llm_summary": review.get("summary", ""),
        })

        state.current_step = f"CriticMaster_{decision}"
        state.update_timestamp()
        state.add_log("CriticMaster", "llm_review", decision, {
            "scores": scores,
            "feedback_count": len(feedback),
            "hallucination_risk": hallucination_risk,
        })

        logger.info(f"[{self.name}] LLM review complete. Final={scores.get('final_score')}, Decision={decision}")
        return state

    # ── LLM Review ───────────────────────────────────────────────────

    async def _llm_review(self, state: ResearchState, report: str) -> dict:
        """Use LLM to review the report quality."""
        # Build context
        outline_summary = "\n".join(
            f"- {s.get('title', '')}" for s in state.outline
        )
        facts_count = len(state.facts)
        sources_count = len(state.filtered_sources)
        data_count = len(state.structured_data.get("companies", {})) + len(state.structured_data.get("industries", {}))

        # Take a representative sample of the report (beginning + middle + end)
        report_sample = report[:2000]
        if len(report) > 6000:
            mid = len(report) // 2
            report_sample += f"\n\n...（中略）...\n\n{report[mid:mid + 1500]}"
        if len(report) > 3000:
            report_sample += f"\n\n...（末尾）...\n\n{report[-1500:]}"

        user_message = f"""请评审以下研究报告。

## 研究任务
{state.user_query}

## 报告大纲
{outline_summary}

## 数据概况
- 检索事实数：{facts_count}
- 信息来源数：{sources_count}
- 分析数据集数：{data_count}
- 报告总长度：{len(report)}字

## 报告内容（节选）
{report_sample[:6000]}

请按评审维度打分并给出路由决策。"""

        try:
            messages = [
                {"role": "system", "content": CRITIC_SYSTEM},
                {"role": "user", "content": user_message},
            ]
            result = await self._llm.chat_json(messages)
            if result.get("_parse_error"):
                logger.warning(f"[{self.name}] LLM review JSON parse failed, using fallback")
                return self._fallback_review(state, report)
            logger.info(f"[{self.name}] LLM review: final={result.get('scores', {}).get('final_score', '?')}, decision={result.get('decision', '?')}")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] LLM review failed: {e}, using fallback")
            return self._fallback_review(state, report)

    # ── Fallback review ──────────────────────────────────────────────

    def _fallback_review(self, state: ResearchState, report: str) -> dict:
        """Rule-based fallback review."""
        import re

        # Completeness: check sections
        total = max(len(state.outline), 1)
        covered = sum(1 for s in state.outline if s.get("title", "") and s["title"] in report)
        completeness = min(95, int(covered / total * 60) + 30)

        # Factuality: based on fact count
        factuality = 90 if len(state.facts) >= 15 else (80 if len(state.facts) >= 8 else (65 if len(state.facts) >= 3 else 45))

        # Logic: transitions + numbers
        transitions = len(re.findall(r'(因此|所以|综上|然而|但是|此外|另外)', report))
        numbers = len(re.findall(r'\d+\.?\d*[万亿]?', report))
        logic = min(95, 70 + transitions * 2 + numbers // 3)

        # Citations
        citations = len(state.filtered_sources) + len(state.evidence_list)
        citation = 90 if citations >= 15 else (80 if citations >= 8 else (65 if citations >= 3 else 40))

        # Data
        data_score = 50
        if state.structured_data.get("companies"):
            data_score += 15
        if state.structured_data.get("industries"):
            data_score += 10
        if state.financial_metrics:
            data_score += 10
        if state.chart_specs:
            data_score += 10
        data_score = min(95, data_score)

        # Readability
        readability = 70
        readability += min(10, len(re.findall(r'^## ', report, re.MULTILINE)))
        readability += min(5, len(re.findall(r'^- ', report, re.MULTILINE)) // 2)
        if 2000 < len(report) < 15000:
            readability += 10
        readability = min(95, readability)

        # Final weighted
        weights = {"completeness_score": 0.25, "factuality_score": 0.25, "logic_score": 0.15, "citation_score": 0.10, "data_score": 0.15, "readability_score": 0.10}
        scores = {"completeness_score": completeness, "factuality_score": factuality, "logic_score": logic, "citation_score": citation, "data_score": data_score, "readability_score": readability}
        final = int(sum(scores.get(k, 70) * w for k, w in weights.items()))
        scores["final_score"] = final

        # Decision
        if final >= 85:
            decision = self.ROUTE_COMPLETE
        elif factuality < 75 or data_score < 75:
            decision = self.ROUTE_RE_RESEARCH
        elif readability < 75 or logic < 75:
            decision = self.ROUTE_REVISE
        else:
            decision = self.ROUTE_COMPLETE

        return {
            "scores": scores,
            "feedback": [f"规则引擎评估：final={final}"],
            "decision": decision,
            "hallucination_risk": "",
            "over_inference": "",
            "summary": "LLM不可用时的规则引擎评估结果",
        }

    @staticmethod
    def _calc_fallback_final(scores: dict) -> int:
        weights = {"completeness_score": 0.25, "factuality_score": 0.25, "logic_score": 0.15, "citation_score": 0.10, "data_score": 0.15, "readability_score": 0.10}
        return int(sum(scores.get(k, 70) * w for k, w in weights.items()))
