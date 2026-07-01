"""Web Search Tool — supports Mock, Serper, Tavily, Brave backends."""

from __future__ import annotations

from typing import Any

from .base import BaseTool
from .backends.web_search import create_web_search_backend, WebSearchBackend


class WebSearchTool(BaseTool):
    """Web search tool with swappable backends.

    Backend selection via .env SEARCH_API_TYPE:
    - mock: Built-in Chinese industry data (default, no API key)
    - serper: Google Search via serper.dev
    - tavily: AI-optimized search via tavily.com
    - brave: Brave Search API

    API Key 获取:
    - Serper: https://serper.dev (免费 2500次/月)
    - Tavily: https://tavily.com (免费 1000次/月)
    - Brave: https://brave.com/search/api/ (免费 2000次/月)
    """

    name: str = "web_search"
    description: str = (
        "网络搜索工具，支持Mock/Serper/Tavily/Brave四种后端。"
        "支持关键词搜索、时间过滤和来源类型筛选。"
    )

    def __init__(self) -> None:
        self._backend: WebSearchBackend = create_web_search_backend()

    async def run(self, input: dict) -> dict:
        """Execute a web search.

        Args:
            input: dict with keys:
                - query (str): Search query
                - top_k (int): Results count (default 5)
                - recency_days (int): Recency filter in days
                - source_type (str): Source type filter

        Returns:
            dict with success status and structured results
        """
        try:
            query = input.get("query", "")
            top_k = input.get("top_k", 5)
            recency_days = input.get("recency_days", 0)
            source_type = input.get("source_type", "")

            if not query:
                return {"success": False, "data": None, "error": "query is required"}

            results = await self._backend.search(query, top_k, recency_days, source_type)

            return {
                "success": True,
                "data": {
                    "query": query,
                    "results": results,
                    "total_found": len(results),
                },
                "error": None,
            }
        except Exception as e:
            # Fallback to mock on any backend error
            from .backends.web_search import MockSearchBackend
            try:
                mock = MockSearchBackend()
                results = await mock.search(input.get("query", ""), input.get("top_k", 5))
                return {"success": True, "data": {"query": input.get("query", ""), "results": results, "total_found": len(results)}, "error": None}
            except Exception:
                return {"success": False, "data": None, "error": str(e)}
