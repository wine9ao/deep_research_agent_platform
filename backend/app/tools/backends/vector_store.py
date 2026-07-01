"""
Vector Store backends — FAISS, Milvus, Qdrant, Mock.

Usage::

    from app.tools.backends.vector_store import create_vector_store_backend
    store = create_vector_store_backend()
    store.add_documents([{"title": "...", "content": "..."}])
    results = store.search("query", top_k=5)
"""

from __future__ import annotations

import math
import os
import re
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any

from ...utils.config import get_settings
from ...utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Abstract backend
# ═══════════════════════════════════════════════════════════════════════════

class VectorStoreBackend(ABC):
    """Abstract interface for vector store backends."""

    @abstractmethod
    def add_documents(self, documents: list[dict[str, str]]) -> None:
        """Add documents with 'title' and 'content' fields."""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5, method: str = "hybrid") -> list[dict]:
        """Search for documents. method: 'vector' | 'bm25' | 'hybrid'."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return number of indexed documents."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# FAISS backend (local, no external service required)
# ═══════════════════════════════════════════════════════════════════════════

class FAISSVectorStore(VectorStoreBackend):
    """FAISS-based vector store (local, fast, production-grade).

    Uses FAISS IndexFlatIP for cosine similarity search.
    Requires: pip install faiss-cpu numpy
    """

    def __init__(self, embedding_dim: int = 768) -> None:
        self.embedding_dim = embedding_dim
        self._documents: list[dict[str, str]] = []
        self._index = None
        self._embeddings: list[list[float]] = []
        self._bm25_store = BM25Store()
        self._init_faiss()

    def _init_faiss(self) -> None:
        """Initialize FAISS index."""
        try:
            import numpy as np
            import faiss
            self._index = faiss.IndexFlatIP(self.embedding_dim)
            self._np = np
            self._faiss = faiss
            logger.info(f"[FAISS] Initialized with dim={self.embedding_dim}")
        except ImportError:
            logger.warning("faiss-cpu not installed. Run: pip install faiss-cpu numpy. Using simple TF-IDF fallback.")
            self._index = None

    def _embed_text(self, text: str) -> list[float]:
        """Create embedding vector for text.

        Uses simple TF-IDF weighted averaging for MVP.
        For production, replace with sentence-transformers or OpenAI embeddings.
        """
        # Simple character n-gram hashing to create a sparse embedding
        # This is a lightweight embedding for demo purposes
        if self._index is None:
            return [0.0] * self.embedding_dim

        # Simple hash-based embedding
        tokens = self._tokenize(text)
        vec = [0.0] * self.embedding_dim
        if not tokens:
            return vec

        for token in tokens:
            h = hash(token) % self.embedding_dim
            vec[h] += 1.0

        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def add_documents(self, documents: list[dict[str, str]]) -> None:
        """Add documents and update FAISS index."""
        for doc in documents:
            self._documents.append(doc)
            text = f"{doc.get('title', '')} {doc.get('content', '')}"
            emb = self._embed_text(text)
            self._embeddings.append(emb)

        # Rebuild FAISS index
        if self._index is not None and self._embeddings:
            try:
                arr = self._np.array(self._embeddings, dtype=self._np.float32)
                self._index.reset()
                self._index.add(arr)
            except Exception as e:
                logger.warning(f"[FAISS] Index update failed: {e}")

        # Also add to BM25 store
        self._bm25_store.add_documents(documents)

    def search(self, query: str, top_k: int = 5, method: str = "hybrid") -> list[dict]:
        """Search the vector store."""
        if not self._documents:
            return []

        if method == "bm25":
            return self._bm25_store.search(query, top_k)
        elif method == "vector":
            return self._vector_search(query, top_k)
        else:  # hybrid
            vec_results = self._vector_search(query, top_k * 2)
            bm25_results = self._bm25_store.search(query, top_k * 2)
            return self._merge_results(vec_results, bm25_results, top_k)

    def _vector_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Vector similarity search."""
        if self._index is None or not self._embeddings:
            # Fallback to simple TF-IDF
            return self._tfidf_search(query, top_k)

        try:
            query_emb = self._embed_text(query)
            arr = self._np.array([query_emb], dtype=self._np.float32)
            distances, indices = self._index.search(arr, min(top_k, len(self._documents)))

            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx >= 0 and idx < len(self._documents):
                    doc = self._documents[idx]
                    results.append({
                        "title": doc["title"],
                        "content_snippet": doc["content"][:300],
                        "score": round(float(dist), 4),
                        "index": int(idx),
                    })
            return results
        except Exception as e:
            logger.warning(f"[FAISS] Search failed: {e}, using TF-IDF fallback")
            return self._tfidf_search(query, top_k)

    def _tfidf_search(self, query: str, top_k: int = 5) -> list[dict]:
        """Simple TF-IDF cosine similarity fallback."""
        query_tokens = self._tokenize(query)
        query_tf = dict(Counter(query_tokens))

        # Compute IDF
        n_docs = max(len(self._documents), 1)
        all_tokens = set(query_tokens)
        for doc in self._documents:
            all_tokens.update(self._tokenize(doc.get("content", "")))

        idf = {}
        for term in all_tokens:
            df = sum(1 for doc in self._documents if term in self._tokenize(doc.get("content", "")))
            idf[term] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

        # Score each document
        scores = []
        for i, doc in enumerate(self._documents):
            doc_tokens = self._tokenize(doc.get("content", ""))
            doc_tf = dict(Counter(doc_tokens))
            dot = sum(query_tf.get(t, 0) * doc_tf.get(t, 0) * idf.get(t, 0) for t in all_tokens)
            q_norm = math.sqrt(sum((query_tf.get(t, 0) * idf.get(t, 0)) ** 2 for t in all_tokens)) or 1
            d_norm = math.sqrt(sum((doc_tf.get(t, 0) * idf.get(t, 0)) ** 2 for t in all_tokens)) or 1
            scores.append((i, dot / (q_norm * d_norm)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {"title": self._documents[i]["title"], "content_snippet": self._documents[i]["content"][:300],
             "score": round(s, 4), "index": i}
            for i, s in scores[:top_k] if s > 0
        ]

    def _merge_results(self, vec: list[dict], bm25: list[dict], top_k: int) -> list[dict]:
        """Merge vector and BM25 results for hybrid search."""
        combined: dict[int, float] = {}
        for r in vec:
            combined[r["index"]] = combined.get(r["index"], 0) + r["score"] * 0.5
        for r in bm25:
            combined[r["index"]] = combined.get(r["index"], 0) + r["score"] * 0.5

        sorted_indices = sorted(combined, key=combined.get, reverse=True)[:top_k]
        return [
            {"title": self._documents[i]["title"], "content_snippet": self._documents[i]["content"][:300],
             "score": round(combined[i], 4), "index": i}
            for i in sorted_indices
        ]

    def count(self) -> int:
        return len(self._documents)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = []
        chinese = re.findall(r'[一-鿿]+', text.lower())
        for seg in chinese:
            for i in range(len(seg) - 1):
                tokens.append(seg[i:i + 2])
            for char in seg:
                tokens.append(char)
        english = re.findall(r'[a-z0-9]+', text.lower())
        tokens.extend(w for w in english if len(w) >= 2)
        return tokens


# ═══════════════════════════════════════════════════════════════════════════
# Milvus backend
# ═══════════════════════════════════════════════════════════════════════════

class MilvusVectorStore(VectorStoreBackend):
    """Milvus vector database backend.

    Requires: pip install pymilvus
    Docker: docker run -d -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest
    """

    def __init__(self, host: str = "localhost", port: int = 19530, dim: int = 768) -> None:
        self.host = host
        self.port = port
        self.dim = dim
        self._collection_name = "deep_research_kb"
        self._collection = None
        self._documents: list[dict] = []
        self._bm25_store = BM25Store()
        self._init_milvus()

    def _init_milvus(self) -> None:
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections

            connections.connect(host=self.host, port=str(self.port))

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            ]
            schema = CollectionSchema(fields, "Deep Research Knowledge Base")

            try:
                self._collection = Collection(self._collection_name)
            except Exception:
                self._collection = Collection(self._collection_name, schema)

            # Create index if not exists
            try:
                self._collection.create_index(
                    field_name="embedding",
                    index_params={"metric_type": "IP", "index_type": "IVF_FLAT", "params": {"nlist": 128}},
                )
            except Exception:
                pass  # Index may already exist

            self._collection.load()
            logger.info(f"[Milvus] Connected to {self.host}:{self.port}, collection='{self._collection_name}'")

        except ImportError:
            raise ImportError("pymilvus not installed. Run: pip install pymilvus")
        except Exception as e:
            raise RuntimeError(f"Milvus connection failed: {e}. Is Milvus running? docker run -d -p 19530:19530 milvusdb/milvus:latest")

    def _embed_text(self, text: str) -> list[float]:
        """Simple hash-based embedding (same as FAISS)."""
        tokens = FAISSVectorStore._tokenize(text)
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        for token in tokens:
            h = hash(token) % self.dim
            vec[h] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec

    def add_documents(self, documents: list[dict[str, str]]) -> None:
        from pymilvus import DataType

        entities = []
        for doc in documents:
            emb = self._embed_text(f"{doc.get('title', '')} {doc.get('content', '')}")
            entities.append({
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
                "embedding": emb,
            })

        if self._collection:
            self._collection.insert(entities)
            self._collection.flush()

        self._documents.extend(documents)
        self._bm25_store.add_documents(documents)
        logger.info(f"[Milvus] Added {len(documents)} documents, total={len(self._documents)}")

    def search(self, query: str, top_k: int = 5, method: str = "hybrid") -> list[dict]:
        if method == "bm25":
            return self._bm25_store.search(query, top_k)

        vector_results = []
        if self._collection and method in ("vector", "hybrid"):
            try:
                query_emb = self._embed_text(query)
                results = self._collection.search(
                    data=[query_emb],
                    anns_field="embedding",
                    param={"metric_type": "IP", "params": {"nprobe": 10}},
                    limit=top_k,
                    output_fields=["title", "content"],
                )
                for hits in results:
                    for hit in hits:
                        vector_results.append({
                            "title": hit.entity.get("title", ""),
                            "content_snippet": hit.entity.get("content", "")[:300],
                            "score": round(hit.distance, 4),
                            "index": hit.id,
                        })
            except Exception as e:
                logger.warning(f"[Milvus] Search failed: {e}")

        if method == "vector":
            return vector_results[:top_k]

        # Hybrid: merge with BM25
        bm25_results = self._bm25_store.search(query, top_k * 2)
        combined: dict[str, float] = {}
        for r in vector_results:
            key = r["title"]
            combined[key] = combined.get(key, 0) + r["score"] * 0.5
        for r in bm25_results:
            key = r["title"]
            combined[key] = combined.get(key, 0) + r["score"] * 0.5

        sorted_keys = sorted(combined, key=combined.get, reverse=True)[:top_k]
        merged = []
        for key in sorted_keys:
            for r in vector_results + bm25_results:
                if r["title"] == key:
                    r["score"] = round(combined[key], 4)
                    merged.append(r)
                    break
        return merged

    def count(self) -> int:
        return len(self._documents) if not self._collection else self._collection.num_entities


# ═══════════════════════════════════════════════════════════════════════════
# Qdrant backend
# ═══════════════════════════════════════════════════════════════════════════

class QdrantVectorStore(VectorStoreBackend):
    """Qdrant vector database backend.

    Requires: pip install qdrant-client
    Docker: docker run -d -p 6333:6333 qdrant/qdrant
    """

    def __init__(self, url: str = "http://localhost:6333", dim: int = 768) -> None:
        self.url = url
        self.dim = dim
        self._collection_name = "deep_research_kb"
        self._client = None
        self._documents: list[dict] = []
        self._bm25_store = BM25Store()
        self._next_id = 0
        self._init_qdrant()

    def _init_qdrant(self) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(url=self.url)

            # Create collection if not exists
            try:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
                )
                logger.info(f"[Qdrant] Created collection '{self._collection_name}'")
            except Exception:
                pass  # Already exists

            logger.info(f"[Qdrant] Connected to {self.url}")
        except ImportError:
            raise ImportError("qdrant-client not installed. Run: pip install qdrant-client")
        except Exception as e:
            raise RuntimeError(f"Qdrant connection failed: {e}. Is Qdrant running? docker run -d -p 6333:6333 qdrant/qdrant")

    def _embed_text(self, text: str) -> list[float]:
        tokens = FAISSVectorStore._tokenize(text)
        vec = [0.0] * self.dim
        if not tokens:
            return vec
        for token in tokens:
            h = hash(token) % self.dim
            vec[h] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        return [v / norm for v in vec] if norm > 0 else vec

    def add_documents(self, documents: list[dict[str, str]]) -> None:
        from qdrant_client.models import PointStruct

        points = []
        for doc in documents:
            emb = self._embed_text(f"{doc.get('title', '')} {doc.get('content', '')}")
            points.append(PointStruct(
                id=self._next_id,
                vector=emb,
                payload={"title": doc.get("title", ""), "content": doc.get("content", "")},
            ))
            self._next_id += 1

        if self._client and points:
            self._client.upsert(collection_name=self._collection_name, points=points)

        self._documents.extend(documents)
        self._bm25_store.add_documents(documents)

    def search(self, query: str, top_k: int = 5, method: str = "hybrid") -> list[dict]:
        if method == "bm25":
            return self._bm25_store.search(query, top_k)

        vector_results = []
        if self._client and method in ("vector", "hybrid"):
            try:
                query_emb = self._embed_text(query)
                results = self._client.search(
                    collection_name=self._collection_name,
                    query_vector=query_emb,
                    limit=top_k,
                )
                for hit in results:
                    vector_results.append({
                        "title": hit.payload.get("title", ""),
                        "content_snippet": hit.payload.get("content", "")[:300],
                        "score": round(hit.score, 4),
                        "index": hit.id,
                    })
            except Exception as e:
                logger.warning(f"[Qdrant] Search failed: {e}")

        if method == "vector":
            return vector_results[:top_k]

        bm25_results = self._bm25_store.search(query, top_k * 2)
        result_map: dict[str, dict] = {}
        for r in vector_results:
            key = r["title"]
            r["score"] = r["score"] * 0.5
            result_map[key] = r
        for r in bm25_results:
            key = r["title"]
            if key in result_map:
                result_map[key]["score"] += r["score"] * 0.5
            else:
                r["score"] = r["score"] * 0.5
                result_map[key] = r

        return sorted(result_map.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    def count(self) -> int:
        if self._client:
            info = self._client.get_collection(self._collection_name)
            return info.points_count
        return len(self._documents)


# ═══════════════════════════════════════════════════════════════════════════
# BM25 Store (shared by all backends for hybrid search)
# ═══════════════════════════════════════════════════════════════════════════

class BM25Store:
    """Lightweight BM25 implementation for keyword search."""

    def __init__(self) -> None:
        self._documents: list[dict[str, str]] = []
        self._doc_terms: list[dict[str, int]] = []
        self._doc_lengths: list[int] = []
        self._avg_dl: float = 0.0
        self._k1: float = 1.5
        self._b: float = 0.75

    def add_documents(self, documents: list[dict[str, str]]) -> None:
        for doc in documents:
            self._documents.append(doc)
            tokens = FAISSVectorStore._tokenize(doc.get("content", "") + " " + doc.get("title", ""))
            self._doc_terms.append(dict(Counter(tokens)))
            self._doc_lengths.append(len(tokens))
        self._avg_dl = sum(self._doc_lengths) / max(len(self._doc_lengths), 1)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self._documents:
            return []
        query_tokens = FAISSVectorStore._tokenize(query)
        n_docs = len(self._documents)

        scores = []
        for i in range(n_docs):
            score = 0.0
            doc_terms = self._doc_terms[i]
            doc_len = self._doc_lengths[i]
            for token in set(query_tokens):
                tf = doc_terms.get(token, 0)
                if tf == 0:
                    continue
                df = sum(1 for dt in self._doc_terms if token in dt)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                tf_score = (tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * doc_len / max(self._avg_dl, 1)))
                score += idf * tf_score
            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [
            {"title": self._documents[i]["title"], "content_snippet": self._documents[i]["content"][:300],
             "score": round(s, 4), "index": i}
            for i, s in scores[:top_k] if s > 0
        ]


# ═══════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════

def create_vector_store_backend() -> VectorStoreBackend:
    """Create the vector store backend based on .env configuration.

    VECTOR_STORE_TYPE=faiss|milvus|qdrant|mock
    """
    settings = get_settings()
    store_type = settings.VECTOR_STORE_TYPE.lower()

    if store_type == "milvus":
        host = os.getenv("MILVUS_HOST", "localhost")
        port = int(os.getenv("MILVUS_PORT", "19530"))
        try:
            logger.info(f"[VectorStore] Using Milvus ({host}:{port})")
            return MilvusVectorStore(host=host, port=port)
        except Exception as e:
            logger.warning(f"[VectorStore] Milvus unavailable ({e}), falling back to FAISS")
            return FAISSVectorStore()

    elif store_type == "qdrant":
        url = os.getenv("QDRANT_URL", "http://localhost:6333")
        try:
            logger.info(f"[VectorStore] Using Qdrant ({url})")
            return QdrantVectorStore(url=url)
        except Exception as e:
            logger.warning(f"[VectorStore] Qdrant unavailable ({e}), falling back to FAISS")
            return FAISSVectorStore()

    else:
        # Default: FAISS (or mock if faiss not installed)
        try:
            import faiss
            logger.info("[VectorStore] Using FAISS backend")
            return FAISSVectorStore()
        except ImportError:
            logger.info("[VectorStore] FAISS not installed, using TF-IDF search (pip install faiss-cpu for better performance)")
            return FAISSVectorStore()  # FAISSVectorStore works without faiss (TF-IDF fallback)
