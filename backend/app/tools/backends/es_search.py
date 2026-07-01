"""
Elasticsearch BM25 keyword search backend.

Usage::

    from app.tools.backends.es_search import ElasticsearchBackend
    es = ElasticsearchBackend()
    es.add_documents([{"title": "...", "content": "..."}])
    results = es.search("query", top_k=5)

Requires:
    pip install elasticsearch
    docker run -d --name es -p 9200:9200 \
      -e "discovery.type=single-node" \
      -e "xpack.security.enabled=false" \
      elasticsearch:8.15.0
"""

from __future__ import annotations

import os
from typing import Any

from ...utils.config import get_settings
from ...utils.logger import get_logger

logger = get_logger(__name__)


class ElasticsearchBackend:
    """Elasticsearch BM25 keyword search backend.

    Features:
    - Full BM25 relevance scoring via ES match queries
    - Chinese text support with standard analyzer
    - Bulk indexing for performance
    - Index stats and document counting
    """

    def __init__(
        self,
        host: str = "http://localhost:9200",
        index_name: str = "deep_research_kb",
    ) -> None:
        self.host = host
        self.index_name = index_name
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize ES client and create index if needed."""
        try:
            from elasticsearch import Elasticsearch

            self._client = Elasticsearch(
                hosts=[self.host],
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True,
            )

            # Test connection
            if not self._client.ping():
                raise RuntimeError(f"Elasticsearch at {self.host} is not responding")

            info = self._client.info()
            logger.info(
                f"[ES] Connected to {self.host}, "
                f"version={info['version']['number']}, "
                f"cluster={info['cluster_name']}"
            )

            # Create index if not exists
            if not self._client.indices.exists(index=self.index_name):
                self._client.indices.create(
                    index=self.index_name,
                    body={
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "analysis": {
                                "analyzer": {
                                    "zh_analyzer": {
                                        "type": "standard",  # Replace with "ik_max_word" when ik plugin installed
                                    }
                                }
                            },
                        },
                        "mappings": {
                            "properties": {
                                "title": {
                                    "type": "text",
                                    "analyzer": "zh_analyzer",
                                    "fields": {"keyword": {"type": "keyword"}},
                                },
                                "content": {
                                    "type": "text",
                                    "analyzer": "zh_analyzer",
                                },
                            }
                        },
                    },
                )
                logger.info(f"[ES] Created index '{self.index_name}'")

        except ImportError:
            raise ImportError("elasticsearch not installed. Run: pip install elasticsearch")
        except Exception as e:
            raise RuntimeError(f"ES connection failed: {e}. Is ES running?")

    # ── Document management ───────────────────────────────────────────

    def add_documents(self, documents: list[dict[str, str]]) -> None:
        """Bulk-index documents into ES.

        Args:
            documents: List of {"title": "...", "content": "..."}
        """
        from elasticsearch.helpers import bulk

        if not documents:
            return

        actions = [
            {
                "_index": self.index_name,
                "_source": {
                    "title": doc.get("title", ""),
                    "content": doc.get("content", ""),
                },
            }
            for doc in documents
        ]

        success, errors = bulk(self._client, actions, refresh=True)
        if errors:
            logger.warning(f"[ES] Bulk index had {len(errors)} errors")
        logger.info(f"[ES] Indexed {success} documents")

    # ── Search ────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """BM25 keyword search via ES match query.

        Args:
            query: Search query string.
            top_k: Max results to return.

        Returns:
            List of {"title", "content_snippet", "score", "index"}
        """
        body = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"title": {"query": query, "boost": 2.0}}},
                        {"match": {"content": {"query": query}}},
                    ]
                }
            },
            "size": top_k,
            "_source": ["title", "content"],
        }

        try:
            response = self._client.search(index=self.index_name, body=body)
            hits = response["hits"]["hits"]

            results = []
            for i, hit in enumerate(hits):
                source = hit["_source"]
                results.append({
                    "title": source.get("title", ""),
                    "content_snippet": source.get("content", "")[:300],
                    "score": round(hit["_score"] / max(hits[0]["_score"], 1), 4) if hits else 0,
                    "index": i,
                })

            return results

        except Exception as e:
            logger.error(f"[ES] Search failed: {e}")
            return []

    # ── Utilities ─────────────────────────────────────────────────────

    def count(self) -> int:
        """Return total document count."""
        try:
            stats = self._client.count(index=self.index_name)
            return stats["count"]
        except Exception:
            return 0

    def delete_index(self) -> None:
        """Delete the entire index (use with caution)."""
        if self._client and self._client.indices.exists(index=self.index_name):
            self._client.indices.delete(index=self.index_name)
            logger.info(f"[ES] Deleted index '{self.index_name}'")

    def is_available(self) -> bool:
        """Check if ES is reachable."""
        try:
            return self._client.ping() if self._client else False
        except Exception:
            return False
