"""Text2SQL API endpoint — natural language to SQL query."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..tools.text2sql import Text2SQLTool
from ..tools.financial_api import FinancialDataAPITool
from ..db.database import get_db_manager

router = APIRouter(prefix="/api/sql", tags=["sql"])

_text2sql = Text2SQLTool(db_path="data/research.db")


class SQLQueryRequest(BaseModel):
    """Request for Text2SQL conversion."""
    question: str = Field(..., description="自然语言问题", min_length=3)


class SQLQueryResponse(BaseModel):
    """Response with SQL and results."""
    sql: str
    result: list
    is_safe: bool
    error: str | None = None


def _init_db_if_needed() -> None:
    """Initialize the SQLite database with mock data if not already done."""
    import os
    db_path = "data/research.db"
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        return

    os.makedirs("data", exist_ok=True)

    api = FinancialDataAPITool()
    companies_data: list[dict] = []
    for company_name, records in api._company_data.items():
        for r in records:
            companies_data.append({"company_name": company_name, **r})

    industries_data: list[dict] = []
    for ind_name, records in api._industry_data.items():
        for r in records:
            industries_data.append({"industry_name": ind_name, **r})

    _text2sql.init_database(companies_data, industries_data)


@router.post("/query", response_model=SQLQueryResponse)
async def text2sql_query(request: SQLQueryRequest) -> SQLQueryResponse:
    """将自然语言问题转换为SQL并执行。

    支持查询公司财务数据（营收、净利润、毛利率等）和行业指标。

    Args:
        request: 自然语言问题。

    Returns:
        生成的SQL、查询结果和安全状态。
    """
    try:
        _init_db_if_needed()

        result = await _text2sql.run({"question": request.question})

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Query failed"))

        return SQLQueryResponse(
            sql=result["sql"],
            result=result["result"],
            is_safe=result["is_safe"],
            error=result.get("error"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
