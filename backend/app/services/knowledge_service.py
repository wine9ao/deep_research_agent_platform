"""Knowledge Service — manages knowledge base documents and retrieval."""

from __future__ import annotations

import os
from typing import Any

from ..db.database import get_db_manager
from ..db.models import KnowledgeDocument
from ..tools.knowledge_base import LocalKnowledgeBaseTool
from ..utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf"}


class KnowledgeService:
    """Manages knowledge base: document upload, listing, and retrieval testing."""

    def __init__(self) -> None:
        self._kb_tool = LocalKnowledgeBaseTool()

    async def upload_document(
        self, filename: str, content: str, file_type: str = "txt"
    ) -> dict:
        """Upload a document to the knowledge base.

        Args:
            filename: Original filename.
            content: Document text content.
            file_type: File type (txt, md, csv, pdf).

        Returns:
            dict with doc_id and status.
        """
        # Validate file type
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS and file_type not in {"txt", "md", "csv", "pdf"}:
            return {"success": False, "error": f"Unsupported file type: {ext}"}

        title = os.path.splitext(filename)[0]

        # Save to database
        db = get_db_manager()
        db.create_all_sync()
        with db.session_factory() as session:
            doc = KnowledgeDocument(
                title=title,
                content=content,
                file_type=file_type or ext.lstrip("."),
                file_path=filename,
                doc_size=len(content.encode("utf-8")),
            )
            session.add(doc)
            session.commit()
            doc_id = doc.doc_id

        # Add to in-memory knowledge base
        self._kb_tool.add_documents([{"title": title, "content": content}])

        logger.info(f"[KnowledgeService] Uploaded document: {title} ({len(content)} chars)")
        return {"success": True, "doc_id": doc_id, "title": title}

    async def list_documents(self) -> list[dict]:
        """List all uploaded documents.

        Returns:
            List of document metadata dicts.
        """
        db = get_db_manager()
        with db.session_factory() as session:
            docs = session.query(KnowledgeDocument).order_by(
                KnowledgeDocument.created_at.desc()
            ).all()
            return [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "file_type": d.file_type,
                    "doc_size": d.doc_size,
                    "created_at": d.created_at.isoformat() if d.created_at else "",
                }
                for d in docs
            ]

    async def search(self, query: str, top_k: int = 5, method: str = "hybrid") -> dict:
        """Search the knowledge base.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            method: 'vector', 'bm25', or 'hybrid'.

        Returns:
            dict with results list.
        """
        result = await self._kb_tool.run({
            "action": "search",
            "query": query,
            "top_k": top_k,
            "method": method,
        })
        return result

    async def delete_document(self, doc_id: str) -> dict:
        """Delete a document from the knowledge base.

        Args:
            doc_id: Document UUID.

        Returns:
            dict with success status.
        """
        db = get_db_manager()
        with db.session_factory() as session:
            doc = session.query(KnowledgeDocument).filter_by(doc_id=doc_id).first()
            if doc:
                session.delete(doc)
                session.commit()
                return {"success": True, "deleted": doc_id}
        return {"success": False, "error": "Document not found"}
