"""Local Knowledge Base Tool — supports FAISS, Milvus, Qdrant backends."""

from __future__ import annotations

from typing import Any

from .base import BaseTool
from .backends.vector_store import create_vector_store_backend, VectorStoreBackend


class LocalKnowledgeBaseTool(BaseTool):
    """Local knowledge base with swappable vector store backends.

    Backend selection via .env VECTOR_STORE_TYPE:
    - faiss: Local FAISS index (default, pip install faiss-cpu)
    - milvus: Milvus vector DB (docker run milvusdb/milvus)
    - qdrant: Qdrant vector DB (docker run qdrant/qdrant)

    All backends support hybrid search (vector + BM25).
    Falls back to TF-IDF if no external dependencies are installed.
    """

    name: str = "local_knowledge_base"
    description: str = (
        "本地知识库工具，支持FAISS/Milvus/Qdrant向量数据库后端。"
        "支持混合检索（向量 + BM25），可导入文档和目录。"
    )

    def __init__(self) -> None:
        self._store: VectorStoreBackend = create_vector_store_backend()

    async def run(self, input: dict) -> dict:
        """Execute knowledge base operations.

        Args:
            input: dict with:
                - action: 'search' | 'add' | 'list' | 'load_mock'
                - query: Search query (for search)
                - top_k: Results count (default 5)
                - method: 'vector' | 'bm25' | 'hybrid' (default hybrid)
                - documents: Documents to add (for add)

        Returns:
            dict with success and data
        """
        try:
            action = input.get("action", "search")

            if action == "load_mock":
                return self._load_mock()

            if action == "add":
                docs = input.get("documents", [])
                self._store.add_documents(docs)
                return {
                    "success": True,
                    "data": {"added_count": len(docs), "total_count": self._store.count()},
                    "error": None,
                }

            if action == "list":
                return {"success": True, "data": {"total_count": self._store.count()}, "error": None}

            if action == "search":
                query = input.get("query", "")
                top_k = input.get("top_k", 5)
                method = input.get("method", "hybrid")

                if not query:
                    return {"success": False, "data": None, "error": "query is required"}

                if self._store.count() == 0:
                    self._load_mock()

                results = self._store.search(query, top_k, method)
                return {
                    "success": True,
                    "data": {"query": query, "results": results, "method": method},
                    "error": None,
                }

            return {"success": False, "data": None, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _load_mock(self) -> dict:
        """Load built-in mock documents."""
        docs = [
            {"title": "动力电池行业分析报告", "content": "2025年中国动力电池行业装机量突破800GWh。宁德时代以43.2%市场份额稳居第一，比亚迪以27.5%位居第二。磷酸铁锂占比提升至67%。行业CR3达到78%。行业产值突破1.5万亿元。政策方面，工信部发布白皮书，支持固态电池等下一代技术研发。碳酸锂价格回落至12万元/吨。"},
            {"title": "AI算力产业链研究", "content": "2025年中国AI算力市场规模预计达4500亿元，同比增长65%。国产AI芯片市占率提升至18%。华为昇腾910B产能爬坡，寒武纪思元590性能达到H100的80%。数据中心功耗和散热问题突出，液冷渗透率快速提升。"},
            {"title": "低空经济政策梳理", "content": "2025年低空经济首次写入政府工作报告。全国28个省份出台低空经济相关政策。亿航智能获全球首张无人驾驶航空器型号合格证。eVTOL适航认证取得突破。2025年市场规模预计达1.2万亿元。"},
            {"title": "白酒行业竞争格局", "content": "2025年白酒行业一超多强。茅台批价2700-2800元，五粮液普五980-1020元。CR5达45%。茅台2024年营收1503亿元，净利润747亿元。消费趋势呈现年轻化、低度化、场景化特点。"},
            {"title": "光伏产业深度分析", "content": "2025年中国光伏新增装机预计250GW，组件价格降至0.7元/W。行业进入产能出清阶段。龙头企业加速海外建厂。N型电池渗透率快速提升，TOPCon和HJT成为主要技术路线。"},
            {"title": "宁德时代公司深度分析", "content": "宁德时代（CATL）全球最大动力电池制造商。2024年营收5230亿元，净利润612亿元。毛利率28.5%，海外收入占比38%。麒麟电池累计装车突破200万辆。固态电池、钠离子电池多线布局。"},
            {"title": "新能源汽车行业发展趋势", "content": "2025年中国新能源汽车销量预计突破1500万辆，渗透率突破50%。1-5月销量620万辆，同比增长38%。出口量预计突破200万辆。智能驾驶渗透率快速提升，城市NOA功能成为新车型标配。"},
        ]
        self._store.add_documents(docs)
        return {"success": True, "data": {"added_count": len(docs), "total_count": self._store.count()}, "error": None}
