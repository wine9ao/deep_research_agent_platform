"""Knowledge Base API endpoints — upload, list, search, delete documents."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_knowledge_service = KnowledgeService()


class SearchRequest(BaseModel):
    """Request to search the knowledge base."""
    query: str = Field(..., description="搜索查询")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    method: str = Field(default="hybrid", description="检索方法: vector, bm25, hybrid")


class DocumentResponse(BaseModel):
    """Document metadata response."""
    doc_id: str
    title: str
    file_type: str
    doc_size: int
    created_at: str


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(default=""),
) -> dict:
    """上传文档到知识库。

    支持 txt, md, csv 格式。

    Args:
        file: 上传的文件。
        title: 可选标题，默认使用文件名。

    Returns:
        上传结果。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read file content
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text_content = content.decode("gbk")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Cannot decode file. Use UTF-8 or GBK encoding.")

    # Determine file type from extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "txt"
    file_type = ext if ext in {"txt", "md", "csv", "pdf"} else "txt"

    result = await _knowledge_service.upload_document(
        filename=file.filename,
        content=text_content,
        file_type=file_type,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Upload failed"))

    return result


@router.get("/documents")
async def list_documents() -> list[DocumentResponse]:
    """列出所有已上传的文档。

    Returns:
        文档列表。
    """
    docs = await _knowledge_service.list_documents()
    return [DocumentResponse(**d) for d in docs]


@router.post("/search")
async def search_knowledge(request: SearchRequest) -> dict:
    """搜索知识库。

    Args:
        request: 搜索参数。

    Returns:
        搜索结果。
    """
    result = await _knowledge_service.search(
        query=request.query,
        top_k=request.top_k,
        method=request.method,
    )
    return result


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    """删除指定文档。

    Args:
        doc_id: 文档UUID。

    Returns:
        删除结果。
    """
    result = await _knowledge_service.delete_document(doc_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Document not found"))
    return result
