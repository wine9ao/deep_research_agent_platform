"""Research API endpoints — create, run, check status, get results."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.research_service import ResearchService

router = APIRouter(prefix="/api/research", tags=["research"])

_research_service = ResearchService()


# ── Request/Response models ───────────────────────────────────────────────


class CreateResearchRequest(BaseModel):
    """Request to create a new research task."""
    query: str = Field(..., description="研究问题", min_length=5, max_length=2000)
    research_type: str = Field(default="", description="研究类型")
    use_mock: bool = Field(default=True, description="是否使用模拟数据")


class CreateResearchResponse(BaseModel):
    """Response after creating a research task."""
    task_id: str
    status: str


class RunResearchResponse(BaseModel):
    """Response after starting a research task."""
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """Response with current task status."""
    task_id: str
    status: str
    current_step: str = ""
    progress: int = 0
    iteration_count: int = 0


class TaskResultResponse(BaseModel):
    """Response with final research results."""
    task_id: str
    status: str
    final_report: str | None = None
    charts: list = []
    sources: list = []
    quality_scores: dict = {}


class TaskLogsResponse(BaseModel):
    """Response with execution logs."""
    task_id: str
    logs: list = []


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.post("/create", response_model=CreateResearchResponse)
async def create_research(request: CreateResearchRequest) -> CreateResearchResponse:
    """创建一个新的研究任务。

    Args:
        request: 包含研究问题、研究类型和是否使用模拟数据。

    Returns:
        任务ID和初始状态。
    """
    result = await _research_service.create_task(
        query=request.query,
        research_type=request.research_type,
        use_mock=request.use_mock,
    )
    return CreateResearchResponse(**result)


@router.post("/run/{task_id}", response_model=RunResearchResponse)
async def run_research(task_id: str) -> RunResearchResponse:
    """启动指定的研究任务。

    任务将在后台异步执行，通过 /status/{task_id} 查看进度。

    Args:
        task_id: 任务UUID。

    Returns:
        任务ID和运行状态。
    """
    result = await _research_service.run_task(task_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Task not found"))
    return RunResearchResponse(**result)


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """获取研究任务的当前状态。

    Args:
        task_id: 任务UUID。

    Returns:
        任务状态、当前步骤和进度。
    """
    result = await _research_service.get_status(task_id)
    return TaskStatusResponse(**result)


@router.get("/result/{task_id}", response_model=TaskResultResponse)
async def get_task_result(task_id: str) -> TaskResultResponse:
    """获取研究任务的最终结果。

    Args:
        task_id: 任务UUID。

    Returns:
        最终报告、图表、来源和质量评分。
    """
    result = await _research_service.get_result(task_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResultResponse(**result)


@router.get("/logs/{task_id}", response_model=TaskLogsResponse)
async def get_task_logs(task_id: str) -> TaskLogsResponse:
    """获取研究任务的执行日志。

    Args:
        task_id: 任务UUID。

    Returns:
        任务执行日志列表。
    """
    result = await _research_service.get_logs(task_id)
    return TaskLogsResponse(**result)
