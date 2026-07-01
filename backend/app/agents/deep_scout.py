"""DeepScout Agent — LLM-enhanced deep information retrieval and evidence collection."""

from __future__ import annotations

from typing import Any

from ..llm.client import get_llm_client
from ..state.research_state import ResearchState
from ..tools.web_search import WebSearchTool
from ..tools.knowledge_base import LocalKnowledgeBaseTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ── LLM prompts ───────────────────────────────────────────────────────────

FACT_EXTRACTION_SYSTEM = """你是一名信息提取专家。从检索结果中提取关键事实。

要求：
1. 每条事实必须来自原文，不要编造
2. 优先提取包含具体数字、百分比、排名的事实
3. 每条事实简洁明了，不超过80字
4. 返回JSON格式：{"facts": ["事实1", "事实2", ...], "key_numbers": [{"metric": "营收", "value": "5230亿元", "company": "宁德时代"}]}
"""

REFLECTION_SYSTEM = """你是一名研究质量审核员。分析当前检索结果，识别信息缺口。

请判断以下方面是否已经覆盖：
1. 行业规模和市场数据
2. 主要企业信息
3. 政策法规
4. 技术发展趋势
5. 风险因素

返回JSON格式：
```json
{
  "coverage_assessment": "good|partial|insufficient",
  "missing_topics": ["缺失的主题1", "缺失的主题2"],
  "suggested_queries": ["建议补充检索的query1", "建议补充检索的query2"],
  "overall_assessment": "综合评估（1-2句话）"
}
```
"""


class DeepScout:
    """Deep Scout Agent — LLM-enhanced multi-source information retrieval.

    Uses LLM for:
    - Fact extraction from search results
    - Relevance and quality reflection
    - Information gap analysis

    Uses Tools for:
    - Web search (WebSearchTool)
    - Knowledge base search (LocalKnowledgeBaseTool)
    """

    name: str = "DeepScout"
    description: str = "深度检索Agent，使用LLM增强多源检索、事实抽取和信息缺口分析。"

    def __init__(self) -> None:
        self._web_search = WebSearchTool()
        self._knowledge_base = LocalKnowledgeBaseTool()
        self._llm = get_llm_client()

    async def execute(self, state: ResearchState) -> ResearchState:
        """Execute LLM-enhanced deep search.

        ReAct loop:
        - Thought: Analyze search plan
        - Action: Execute web + KB searches
        - Observation: Collect and score results
        - Reflection: LLM analyzes coverage and identifies gaps
        """
        logger.info(f"[{self.name}] Starting LLM-enhanced search with {len(state.search_plan)} queries...")
        state.add_log("DeepScout", "execute", "start", {"query_count": len(state.search_plan)})

        search_plan = state.search_plan if state.search_plan else [
            {"query": state.user_query, "source_type": "news", "priority": 1}
        ]

        # ── Phase 1: Execute all searches ────────────────────────────
        all_results: list[dict] = []

        for i, plan_item in enumerate(search_plan):
            query = plan_item["query"]
            source_type = plan_item.get("source_type", "news")
            priority = plan_item.get("priority", 2)

            state.add_log("DeepScout", "search", f"query_{i + 1}", {
                "query": query, "source_type": source_type,
            })

            # Thought → Action → Observation
            web_result = await self._web_search.run({
                "query": query, "top_k": 5, "source_type": source_type,
            })
            if web_result["success"] and web_result["data"]:
                for r in web_result["data"]["results"]:
                    all_results.append({**r, "query_used": query, "priority": priority})

            kb_result = await self._knowledge_base.run({
                "action": "search", "query": query, "top_k": 3, "method": "hybrid",
            })
            if kb_result["success"] and kb_result["data"]:
                for r in kb_result["data"]["results"]:
                    all_results.append({
                        "title": r["title"], "url": "local://kb", "source": "本地知识库",
                        "snippet": r["content_snippet"],
                        "relevance_score": r.get("score", 0.5),
                        "freshness_score": 0.5,
                        "final_score": r.get("score", 0.5),
                        "query_used": query, "priority": priority,
                    })

        # ── Phase 2: Deduplicate & rank ──────────────────────────────
        state.raw_search_results = all_results
        seen_titles = set()
        deduped = []
        for r in all_results:
            title_key = r["title"][:60]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                deduped.append(r)
        deduped.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        state.filtered_sources = deduped[:20]

        # ── Phase 3: LLM fact extraction ─────────────────────────────
        state.evidence_list, state.facts = await self._llm_extract_facts(deduped[:15])

        # ── Phase 4: LLM reflection on coverage ──────────────────────
        state.missing_information = await self._llm_reflection(state)

        state.current_step = "DeepScout_complete"
        state.update_timestamp()
        state.add_log("DeepScout", "llm_reflection", "complete", {
            "total_results": len(deduped),
            "llm_facts": len(state.facts),
            "missing_count": len(state.missing_information),
        })

        logger.info(
            f"[{self.name}] Search complete. Results={len(deduped)}, "
            f"LLM-facts={len(state.facts)}, Gaps={len(state.missing_information)}"
        )
        return state

    # ── LLM: Fact extraction ──────────────────────────────────────────

    async def _llm_extract_facts(self, results: list[dict]) -> tuple[list[dict], list[str]]:
        """Use LLM to extract structured facts from search results."""
        evidence_list = []
        all_facts = []

        for i, r in enumerate(results[:10]):
            evidence = {
                "title": r["title"],
                "source": r.get("source", "未知来源"),
                "url": r.get("url", ""),
                "publish_time": r.get("publish_time", ""),
                "excerpt": r.get("snippet", "")[:300],
                "relevance": r.get("final_score", 0),
            }
            evidence_list.append(evidence)

        # Build context for LLM
        snippets_text = "\n\n---\n\n".join(
            f"[来源{i + 1}] {r['title']}\n{r.get('snippet', '')[:300]}"
            for i, r in enumerate(results[:10])
        )

        try:
            messages = [
                {"role": "system", "content": FACT_EXTRACTION_SYSTEM},
                {"role": "user", "content": f"请从以下检索结果中提取关键事实：\n\n{snippets_text[:4000]}"},
            ]
            llm_result = await self._llm.chat_json(messages)
            if not llm_result.get("_parse_error"):
                all_facts = llm_result.get("facts", [])
                logger.info(f"[{self.name}] LLM extracted {len(all_facts)} facts")
        except Exception as e:
            logger.warning(f"[{self.name}] LLM fact extraction failed: {e}, using rule-based fallback")

        # Fallback: rule-based extraction
        if not all_facts:
            for r in results:
                snippet = r.get("snippet", "")
                if snippet:
                    sentences = snippet.replace("。", "。\n").split("\n")
                    for sent in sentences:
                        clean = sent.strip()
                        if len(clean) > 15 and any(kw in clean for kw in ["万", "亿", "%", "增长", "下降", "排名", "第一", "占比"]):
                            all_facts.append(clean)

        return evidence_list, list(dict.fromkeys(all_facts))[:30]

    # ── LLM: Reflection ───────────────────────────────────────────────

    async def _llm_reflection(self, state: ResearchState) -> list[str]:
        """Use LLM to analyze search coverage and identify gaps."""
        # Build context
        outline_titles = [s.get("title", "") for s in state.outline]
        facts_summary = "\n".join(f"- {f}" for f in state.facts[:15])
        sources_summary = "\n".join(
            f"- [{r.get('source', '?')}] {r['title'][:80]}"
            for r in state.filtered_sources[:10]
        )

        reflection_prompt = f"""研究问题：{state.user_query}

研究大纲章节：
{chr(10).join(outline_titles)}

已检索到的事实（部分）：
{facts_summary}

检索来源（部分）：
{sources_summary}

总共检索到{len(state.filtered_sources)}条结果，{len(state.facts)}条事实。

请分析信息覆盖情况，识别缺失的主题。"""

        try:
            messages = [
                {"role": "system", "content": REFLECTION_SYSTEM},
                {"role": "user", "content": reflection_prompt[:4000]},
            ]
            llm_result = await self._llm.chat_json(messages)
            if not llm_result.get("_parse_error"):
                missing = llm_result.get("missing_topics", [])
                assessment = llm_result.get("overall_assessment", "")
                logger.info(f"[{self.name}] LLM reflection: coverage={llm_result.get('coverage_assessment')}, gaps={len(missing)}")
                state.add_log("DeepScout", "llm_reflection_detail", "coverage", {
                    "assessment": assessment,
                    "coverage": llm_result.get("coverage_assessment", "?"),
                })
                return missing
        except Exception as e:
            logger.warning(f"[{self.name}] LLM reflection failed: {e}, using rule-based fallback")

        # Fallback
        gaps = []
        covered_topics = " ".join(r.get("snippet", "") + r.get("title", "") for r in state.filtered_sources)
        for title in outline_titles:
            short = title.replace("一、", "").replace("二、", "").replace("三、", "").replace("四、", "").replace("五、", "").replace("六、", "").replace("七、", "").replace("八、", "").replace("九、", "").replace("十、", "").replace("附录：", "")
            if short and short not in covered_topics:
                gaps.append(f"缺少「{title}」相关的信息")
        if len(state.facts) < 5:
            gaps.append("检索到的事实性信息较少，建议扩大检索范围")
        return gaps[:5]
