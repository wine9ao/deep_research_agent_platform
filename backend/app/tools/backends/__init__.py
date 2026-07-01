"""Tool backends — swappable implementations for each tool.

Each tool supports multiple backends selected via .env configuration:
- Web search: mock | serper | tavily | brave
- Financial data: mock | tushare | akshare
- Vector store: faiss | mock | milvus | qdrant
"""

from .web_search import create_web_search_backend
from .financial import create_financial_backend
from .vector_store import create_vector_store_backend

__all__ = [
    "create_web_search_backend",
    "create_financial_backend",
    "create_vector_store_backend",
]
