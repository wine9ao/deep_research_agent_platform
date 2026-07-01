"""Financial Data API Tool — supports Mock, Tushare, AKShare backends."""

from __future__ import annotations

from typing import Any

from .base import BaseTool
from .backends.financial import create_financial_backend, FinancialBackend


class FinancialDataAPITool(BaseTool):
    """Financial data API with swappable backends.

    Backend selection via .env FINANCIAL_API_TYPE:
    - mock: Built-in data for 5 companies + 6 industries (default, no key)
    - tushare: Tushare Pro API (需要 token, https://tushare.pro)
    - akshare: AKShare (免费, 无需 API Key, pip install akshare)

    Covers:
    - Companies: 宁德时代, 比亚迪, 亿纬锂能, 国轩高科, 中创新航
    - Industries: 动力电池, 新能源汽车, AI算力, 低空经济, 白酒, 光伏
    - Years: 2022-2025
    """

    name: str = "financial_data_api"
    description: str = (
        "金融数据API工具，支持Mock/Tushare/AKShare三种后端。"
        "查询公司财务数据（营收、净利润、毛利率、ROE等）和行业指标。"
    )

    def __init__(self) -> None:
        self._backend: FinancialBackend = create_financial_backend()

    async def run(self, input: dict) -> dict:
        """Query financial data.

        Args:
            input: dict with:
                - query_type: 'company' or 'industry'
                - company_names: list of company names
                - industry_names: list of industry names
                - years: list of years to filter

        Returns:
            dict with success and data
        """
        try:
            query_type = input.get("query_type", "company")
            company_names = input.get("company_names", [])
            industry_names = input.get("industry_names", [])
            years = input.get("years", [])

            if query_type == "company":
                data = await self._backend.get_company_data(company_names, years or None)
            elif query_type == "industry":
                data = await self._backend.get_industry_data(industry_names, years or None)
            else:
                return {"success": False, "data": None, "error": f"Unknown query_type: {query_type}"}

            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    @classmethod
    def get_available_companies(cls) -> list[str]:
        return ["宁德时代", "比亚迪", "亿纬锂能", "国轩高科", "中创新航"]

    @classmethod
    def get_available_industries(cls) -> list[str]:
        return ["动力电池", "新能源汽车", "AI算力", "低空经济", "白酒", "光伏"]
