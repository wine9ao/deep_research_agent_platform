"""Local Knowledge Base Tool — supports FAISS, Milvus, Qdrant + Elasticsearch BM25."""

from __future__ import annotations

import os
from typing import Any

from .base import BaseTool
from .backends.vector_store import create_vector_store_backend, VectorStoreBackend
from ..utils.config import get_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LocalKnowledgeBaseTool(BaseTool):
    """Knowledge base with swappable vector + keyword search backends.

    Vector backends (.env VECTOR_STORE_TYPE):
        faiss | milvus | qdrant

    Keyword search backends (.env SEARCH_BACKEND):
        bm25 (default) | elasticsearch

    All backends support hybrid search (vector + keyword).
    """

    name: str = "local_knowledge_base"
    description: str = (
        "本地知识库工具，向量检索(FAISS/Milvus/Qdrant) + "
        "关键词检索(BM25/Elasticsearch)，支持混合检索。"
    )

    def __init__(self) -> None:
        self._store: VectorStoreBackend = create_vector_store_backend()
        self._es = self._init_es()

    def _init_es(self):
        """Try to initialize ES if configured."""
        settings = get_settings()
        search_backend = os.getenv("SEARCH_BACKEND", "bm25").lower()
        if search_backend != "elasticsearch":
            return None
        try:
            from .backends.es_search import ElasticsearchBackend
            es_host = os.getenv("ES_HOST", "http://localhost:9200")
            es = ElasticsearchBackend(host=es_host)
            if es.is_available():
                logger.info("[KB] Elasticsearch BM25 enabled")
                return es
            else:
                logger.warning("[KB] ES configured but not reachable, using Python BM25")
                return None
        except Exception as e:
            logger.warning(f"[KB] ES init failed: {e}, using Python BM25")
            return None

    async def run(self, input: dict) -> dict:
        try:
            action = input.get("action", "search")

            if action == "load_mock":
                return self._load_mock()

            if action == "add":
                docs = input.get("documents", [])
                self._store.add_documents(docs)
                if self._es:
                    self._es.add_documents(docs)
                return {
                    "success": True,
                    "data": {"added_count": len(docs), "total_count": self._store.count()},
                    "error": None,
                }

            if action == "list":
                total = self._store.count()
                if self._es:
                    total = max(total, self._es.count())
                return {"success": True, "data": {"total_count": total}, "error": None}

            if action == "search":
                query = input.get("query", "")
                top_k = input.get("top_k", 5)
                method = input.get("method", "hybrid")

                if not query:
                    return {"success": False, "data": None, "error": "query is required"}

                if self._store.count() == 0:
                    self._load_mock()

                results = self._do_search(query, top_k, method)
                return {
                    "success": True,
                    "data": {"query": query, "results": results, "method": method},
                    "error": None,
                }

            return {"success": False, "data": None, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _do_search(self, query: str, top_k: int, method: str) -> list[dict]:
        """Execute search using the configured backends."""
        if method == "bm25" and self._es:
            return self._es.search(query, top_k)
        elif method == "bm25":
            return self._store.search(query, top_k, method="bm25")
        elif method == "vector":
            return self._store.search(query, top_k, method="vector")
        else:  # hybrid
            vec_results = self._store.search(query, top_k * 2, method="vector")
            if self._es:
                kw_results = self._es.search(query, top_k * 2)
            else:
                kw_results = self._store.search(query, top_k * 2, method="bm25")
            return self._merge(vec_results, kw_results, top_k)

    @staticmethod
    def _merge(vec: list[dict], kw: list[dict], top_k: int) -> list[dict]:
        """Merge vector and keyword results."""
        combined: dict[str, float] = {}
        details: dict[str, dict] = {}
        for r in vec:
            key = r["title"]
            combined[key] = combined.get(key, 0) + r.get("score", 0) * 0.5
            details[key] = r
        for r in kw:
            key = r["title"]
            combined[key] = combined.get(key, 0) + r.get("score", 0) * 0.5
            if key not in details:
                details[key] = r

        sorted_keys = sorted(combined, key=combined.get, reverse=True)[:top_k]
        result = []
        for key in sorted_keys:
            item = dict(details.get(key, {}))
            item["score"] = round(combined[key], 4)
            result.append(item)
        return result

    def _load_mock(self) -> dict:
        docs = [
            {"title": "动力电池行业分析报告", "content": "2025年中国动力电池行业装机量突破800GWh。宁德时代以43.2%市场份额稳居第一，比亚迪以27.5%位居第二。磷酸铁锂占比提升至67%。行业CR3达到78%。"},
            {"title": "AI算力产业链研究", "content": "2025年中国AI算力市场规模预计达4500亿元，同比增长65%。国产AI芯片市占率提升至18%。华为昇腾910B产能爬坡。"},
            {"title": "低空经济政策梳理", "content": "2025年低空经济首次写入政府工作报告。全国28个省份出台低空经济相关政策。亿航智能获全球首张无人驾驶航空器型号合格证。"},
            {"title": "白酒行业竞争格局", "content": "2025年白酒行业一超多强。茅台批价2700-2800元。CR5达45%。茅台2024年营收1503亿元，净利润747亿元。"},
            {"title": "光伏产业深度分析", "content": "2025年中国光伏新增装机预计250GW，组件价格降至0.7元/W。N型电池渗透率快速提升。"},
            {"title": "宁德时代公司深度分析", "content": "宁德时代2024年营收5230亿元，净利润612亿元。毛利率28.5%，海外收入占比38%。麒麟电池累计装车突破200万辆。"},
            {"title": "新能源汽车行业发展趋势", "content": "2025年中国新能源汽车销量预计突破1500万辆，渗透率突破50%。出口量预计突破200万辆。智能驾驶渗透率快速提升。"},
        ]
        self._store.add_documents(docs)
        if self._es:
            self._es.add_documents(docs)
        return {"success": True, "data": {"added_count": len(docs), "total_count": self._store.count()}, "error": None}
