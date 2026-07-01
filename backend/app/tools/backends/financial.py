"""
Financial data backends — Mock, Tushare, AKShare.

Usage::

    from app.tools.backends.financial import create_financial_backend
    backend = create_financial_backend()
    data = await backend.get_company_data(["宁德时代"])
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from ...utils.config import get_settings
from ...utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Mock data (same as before — always available)
# ═══════════════════════════════════════════════════════════════════════════

_MOCK_COMPANY_DATA: dict[str, list[dict[str, Any]]] = {
    "宁德时代": [
        {"year": 2022, "revenue": 3286, "net_profit": 307, "gross_margin": 0.283, "net_margin": 0.093, "roe": 0.215, "debt_ratio": 0.585, "market_share": 0.372},
        {"year": 2023, "revenue": 4009, "net_profit": 441, "gross_margin": 0.275, "net_margin": 0.110, "roe": 0.228, "debt_ratio": 0.562, "market_share": 0.395},
        {"year": 2024, "revenue": 5230, "net_profit": 612, "gross_margin": 0.285, "net_margin": 0.117, "roe": 0.245, "debt_ratio": 0.548, "market_share": 0.432},
        {"year": 2025, "revenue": 6200, "net_profit": 750, "gross_margin": 0.290, "net_margin": 0.121, "roe": 0.252, "debt_ratio": 0.530, "market_share": 0.450},
    ],
    "比亚迪": [
        {"year": 2022, "revenue": 4241, "net_profit": 166, "gross_margin": 0.170, "net_margin": 0.039, "roe": 0.121, "debt_ratio": 0.658, "market_share": 0.225},
        {"year": 2023, "revenue": 6023, "net_profit": 300, "gross_margin": 0.195, "net_margin": 0.050, "roe": 0.168, "debt_ratio": 0.632, "market_share": 0.248},
        {"year": 2024, "revenue": 7800, "net_profit": 420, "gross_margin": 0.210, "net_margin": 0.054, "roe": 0.185, "debt_ratio": 0.610, "market_share": 0.275},
        {"year": 2025, "revenue": 9500, "net_profit": 550, "gross_margin": 0.218, "net_margin": 0.058, "roe": 0.192, "debt_ratio": 0.595, "market_share": 0.290},
    ],
    "亿纬锂能": [
        {"year": 2022, "revenue": 223, "net_profit": 24, "gross_margin": 0.238, "net_margin": 0.108, "roe": 0.142, "debt_ratio": 0.521, "market_share": 0.042},
        {"year": 2023, "revenue": 287, "net_profit": 32, "gross_margin": 0.245, "net_margin": 0.111, "roe": 0.158, "debt_ratio": 0.505, "market_share": 0.048},
        {"year": 2024, "revenue": 382, "net_profit": 48, "gross_margin": 0.252, "net_margin": 0.126, "roe": 0.178, "debt_ratio": 0.488, "market_share": 0.055},
        {"year": 2025, "revenue": 500, "net_profit": 68, "gross_margin": 0.258, "net_margin": 0.136, "roe": 0.190, "debt_ratio": 0.470, "market_share": 0.062},
    ],
    "国轩高科": [
        {"year": 2022, "revenue": 186, "net_profit": 18, "gross_margin": 0.195, "net_margin": 0.097, "roe": 0.098, "debt_ratio": 0.612, "market_share": 0.032},
        {"year": 2023, "revenue": 235, "net_profit": 25, "gross_margin": 0.202, "net_margin": 0.106, "roe": 0.112, "debt_ratio": 0.595, "market_share": 0.035},
        {"year": 2024, "revenue": 282, "net_profit": 32, "gross_margin": 0.210, "net_margin": 0.113, "roe": 0.125, "debt_ratio": 0.580, "market_share": 0.038},
        {"year": 2025, "revenue": 350, "net_profit": 42, "gross_margin": 0.215, "net_margin": 0.120, "roe": 0.138, "debt_ratio": 0.565, "market_share": 0.040},
    ],
    "中创新航": [
        {"year": 2022, "revenue": 142, "net_profit": 11, "gross_margin": 0.178, "net_margin": 0.077, "roe": 0.078, "debt_ratio": 0.645, "market_share": 0.025},
        {"year": 2023, "revenue": 185, "net_profit": 15, "gross_margin": 0.185, "net_margin": 0.081, "roe": 0.088, "debt_ratio": 0.628, "market_share": 0.028},
        {"year": 2024, "revenue": 256, "net_profit": 22, "gross_margin": 0.192, "net_margin": 0.086, "roe": 0.102, "debt_ratio": 0.605, "market_share": 0.032},
        {"year": 2025, "revenue": 320, "net_profit": 30, "gross_margin": 0.198, "net_margin": 0.094, "roe": 0.115, "debt_ratio": 0.590, "market_share": 0.035},
    ],
}

_MOCK_INDUSTRY_DATA: dict[str, list[dict[str, Any]]] = {
    "动力电池": [
        {"year": 2022, "market_size": 6800, "growth_rate": 0.68, "policy_count": 15, "investment_amount": 3200, "penetration_rate": 0.32},
        {"year": 2023, "market_size": 10500, "growth_rate": 0.54, "policy_count": 22, "investment_amount": 4500, "penetration_rate": 0.40},
        {"year": 2024, "market_size": 15200, "growth_rate": 0.42, "policy_count": 28, "investment_amount": 5800, "penetration_rate": 0.52},
        {"year": 2025, "market_size": 18500, "growth_rate": 0.28, "policy_count": 32, "investment_amount": 6800, "penetration_rate": 0.61},
    ],
    "新能源汽车": [
        {"year": 2022, "market_size": 36800, "growth_rate": 0.95, "policy_count": 18, "investment_amount": 8500, "penetration_rate": 0.256},
        {"year": 2023, "market_size": 52000, "growth_rate": 0.41, "policy_count": 25, "investment_amount": 11000, "penetration_rate": 0.356},
        {"year": 2024, "market_size": 68000, "growth_rate": 0.31, "policy_count": 30, "investment_amount": 13500, "penetration_rate": 0.462},
        {"year": 2025, "market_size": 82000, "growth_rate": 0.21, "policy_count": 35, "investment_amount": 15000, "penetration_rate": 0.550},
    ],
    "AI算力": [
        {"year": 2022, "market_size": 1200, "growth_rate": 0.45, "policy_count": 8, "investment_amount": 800, "penetration_rate": 0.08},
        {"year": 2023, "market_size": 1800, "growth_rate": 0.50, "policy_count": 12, "investment_amount": 1500, "penetration_rate": 0.12},
        {"year": 2024, "market_size": 3000, "growth_rate": 0.67, "policy_count": 20, "investment_amount": 3200, "penetration_rate": 0.18},
        {"year": 2025, "market_size": 4500, "growth_rate": 0.65, "policy_count": 28, "investment_amount": 5500, "penetration_rate": 0.25},
    ],
    "低空经济": [
        {"year": 2022, "market_size": 3800, "growth_rate": 0.30, "policy_count": 5, "investment_amount": 200, "penetration_rate": 0.02},
        {"year": 2023, "market_size": 5500, "growth_rate": 0.45, "policy_count": 12, "investment_amount": 500, "penetration_rate": 0.04},
        {"year": 2024, "market_size": 8500, "growth_rate": 0.55, "policy_count": 22, "investment_amount": 1200, "penetration_rate": 0.08},
        {"year": 2025, "market_size": 12000, "growth_rate": 0.41, "policy_count": 30, "investment_amount": 2500, "penetration_rate": 0.12},
    ],
    "白酒": [
        {"year": 2022, "market_size": 6200, "growth_rate": 0.08, "policy_count": 3, "investment_amount": 300, "penetration_rate": 0.85},
        {"year": 2023, "market_size": 6800, "growth_rate": 0.10, "policy_count": 5, "investment_amount": 350, "penetration_rate": 0.86},
        {"year": 2024, "market_size": 7500, "growth_rate": 0.10, "policy_count": 6, "investment_amount": 400, "penetration_rate": 0.87},
        {"year": 2025, "market_size": 8000, "growth_rate": 0.07, "policy_count": 8, "investment_amount": 450, "penetration_rate": 0.88},
    ],
    "光伏": [
        {"year": 2022, "market_size": 15000, "growth_rate": 0.55, "policy_count": 20, "investment_amount": 6000, "penetration_rate": 0.15},
        {"year": 2023, "market_size": 21000, "growth_rate": 0.40, "policy_count": 25, "investment_amount": 7500, "penetration_rate": 0.20},
        {"year": 2024, "market_size": 26000, "growth_rate": 0.24, "policy_count": 28, "investment_amount": 8000, "penetration_rate": 0.25},
        {"year": 2025, "market_size": 30000, "growth_rate": 0.15, "policy_count": 30, "investment_amount": 8500, "penetration_rate": 0.30},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# Abstract backend
# ═══════════════════════════════════════════════════════════════════════════

class FinancialBackend(ABC):
    """Abstract interface for financial data backends."""

    @abstractmethod
    async def get_company_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        ...

    @abstractmethod
    async def get_industry_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        ...

    def get_available_companies(self) -> list[str]:
        return list(_MOCK_COMPANY_DATA.keys())

    def get_available_industries(self) -> list[str]:
        return list(_MOCK_INDUSTRY_DATA.keys())


# ═══════════════════════════════════════════════════════════════════════════
# Mock backend
# ═══════════════════════════════════════════════════════════════════════════

class MockFinancialBackend(FinancialBackend):
    """Built-in mock financial data."""

    async def get_company_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        result = {}
        for name in names:
            if name in _MOCK_COMPANY_DATA:
                records = _MOCK_COMPANY_DATA[name]
                if years:
                    records = [r for r in records if r["year"] in years]
                result[name] = records
        return result

    async def get_industry_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        result = {}
        for name in names:
            if name in _MOCK_INDUSTRY_DATA:
                records = _MOCK_INDUSTRY_DATA[name]
                if years:
                    records = [r for r in records if r["year"] in years]
                result[name] = records
        return result


# ═══════════════════════════════════════════════════════════════════════════
# Tushare backend (real Chinese financial data)
# ═══════════════════════════════════════════════════════════════════════════
# Token 获取: https://tushare.pro — 注册即送积分


class TushareFinancialBackend(FinancialBackend):
    """Real financial data via Tushare Pro API.

    Requires: pip install tushare
    Token: https://tushare.pro → 注册 → 个人中心 → 接口Token
    """

    def __init__(self, token: str) -> None:
        self.token = token
        self._pro = None

    def _get_pro(self):
        if self._pro is None:
            try:
                import tushare as ts
                ts.set_token(self.token)
                self._pro = ts.pro_api()
                logger.info("[Tushare] Connected successfully")
            except ImportError:
                raise ImportError("tushare not installed. Run: pip install tushare")
            except Exception as e:
                raise RuntimeError(f"Tushare init failed: {e}")
        return self._pro

    async def get_company_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        """Query company financial data via Tushare.

        Maps Chinese company names to Tushare stock codes and fetches
        income statement + financial indicators.
        """
        # Tushare stock code mapping
        CODE_MAP = {
            "宁德时代": "300750.SZ",
            "比亚迪": "002594.SZ",
            "亿纬锂能": "300014.SZ",
            "国轩高科": "002074.SZ",
            "中创新航": "03931.HK",
        }

        result = {}
        try:
            pro = self._get_pro()
            target_years = years or [2022, 2023, 2024, 2025]

            for name in names:
                ts_code = CODE_MAP.get(name)
                if not ts_code:
                    logger.warning(f"[Tushare] Unknown company: {name}")
                    continue

                records = []
                for year in target_years:
                    try:
                        # Fetch income statement
                        income = pro.income(
                            ts_code=ts_code,
                            start_date=f"{year}0101",
                            end_date=f"{year}1231",
                            fields="ts_code,end_date,revenue,n_income",
                        )
                        # Fetch financial indicators
                        indicators = pro.fina_indicator(
                            ts_code=ts_code,
                            start_date=f"{year}0101",
                            end_date=f"{year}1231",
                            fields="ts_code,grossprofit_margin,netprofit_margin,roe,debt_to_assets",
                        )

                        if not income.empty:
                            row = income.iloc[0]
                            ind_row = indicators.iloc[0] if not indicators.empty else None
                            records.append({
                                "year": year,
                                "revenue": round(float(row.get("revenue", 0)) / 1e8, 2) if row.get("revenue") else 0,
                                "net_profit": round(float(row.get("n_income", 0)) / 1e8, 2) if row.get("n_income") else 0,
                                "gross_margin": round(float(ind_row.get("grossprofit_margin", 0)) / 100, 4) if ind_row is not None and ind_row.get("grossprofit_margin") else 0,
                                "net_margin": round(float(ind_row.get("netprofit_margin", 0)) / 100, 4) if ind_row is not None and ind_row.get("netprofit_margin") else 0,
                                "roe": round(float(ind_row.get("roe", 0)) / 100, 4) if ind_row is not None and ind_row.get("roe") else 0,
                                "debt_ratio": round(float(ind_row.get("debt_to_assets", 0)) / 100, 4) if ind_row is not None and ind_row.get("debt_to_assets") else 0,
                                "market_share": 0,
                            })
                    except Exception as e:
                        logger.warning(f"[Tushare] Failed for {name} {year}: {e}")

                if records:
                    result[name] = records

            logger.info(f"[Tushare] Got data for {len(result)} companies")
            return result

        except Exception as e:
            logger.error(f"[Tushare] Query failed: {e}, falling back to mock")
            return await MockFinancialBackend().get_company_data(names, years)

    async def get_industry_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        """Tushare doesn't have direct industry-level data, fall back to mock."""
        logger.info("[Tushare] Industry data not available, using mock")
        return await MockFinancialBackend().get_industry_data(names, years)


# ═══════════════════════════════════════════════════════════════════════════
# AKShare backend (free Chinese financial data)
# ═══════════════════════════════════════════════════════════════════════════
# 无需 API Key，完全免费开源
# pip install akshare


class AKShareFinancialBackend(FinancialBackend):
    """Real financial data via AKShare (free, no API key required).

    Requires: pip install akshare
    """

    async def get_company_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        """Query company financial data via AKShare."""
        CODE_MAP = {
            "宁德时代": "300750",
            "比亚迪": "002594",
            "亿纬锂能": "300014",
            "国轩高科": "002074",
            "中创新航": "03931",
        }

        result = {}
        try:
            import akshare as ak

            target_years = years or [2022, 2023, 2024, 2025]

            for name in names:
                symbol = CODE_MAP.get(name)
                if not symbol:
                    continue

                records = []
                try:
                    # Fetch financial indicators
                    df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按年度")
                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            try:
                                year = int(str(row.get("报告期", ""))[:4])
                                if year in target_years:
                                    records.append({
                                        "year": year,
                                        "revenue": round(float(row.get("营业总收入", 0)) / 1e8, 2),
                                        "net_profit": round(float(row.get("净利润", 0)) / 1e8, 2),
                                        "gross_margin": round(float(row.get("毛利率", 0)) / 100, 4),
                                        "net_margin": round(float(row.get("净利率", 0)) / 100, 4),
                                        "roe": round(float(row.get("ROE", 0)) / 100, 4),
                                        "debt_ratio": round(float(row.get("资产负债率", 0)) / 100, 4),
                                        "market_share": 0,
                                    })
                            except (ValueError, TypeError):
                                continue
                except Exception as e:
                    logger.warning(f"[AKShare] Failed for {name}: {e}")

                if records:
                    result[name] = records

            logger.info(f"[AKShare] Got data for {len(result)} companies")
            return result

        except ImportError:
            logger.warning("AKShare not installed. Run: pip install akshare. Using mock data.")
            return await MockFinancialBackend().get_company_data(names, years)
        except Exception as e:
            logger.error(f"[AKShare] Query failed: {e}, using mock")
            return await MockFinancialBackend().get_company_data(names, years)

    async def get_industry_data(self, names: list[str], years: list[int] | None = None) -> dict[str, list[dict]]:
        """AKShare industry data (limited). Falls back to mock."""
        try:
            import akshare as ak
            result = {}
            for name in names:
                try:
                    df = ak.macro_china()
                    if df is not None:
                        # Generic industry data — actual implementation depends on specific AKShare functions
                        pass
                except Exception:
                    pass
            if not result:
                logger.info("[AKShare] Industry data not found, using mock")
                return await MockFinancialBackend().get_industry_data(names, years)
            return result
        except Exception:
            return await MockFinancialBackend().get_industry_data(names, years)


# ═══════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════

def create_financial_backend() -> FinancialBackend:
    """Create the financial data backend based on .env configuration.

    FINANCIAL_API_TYPE=mock|tushare|akshare
    """
    settings = get_settings()
    api_type = settings.FINANCIAL_API_TYPE.lower()

    if api_type == "tushare":
        token = os.getenv("TUSHARE_TOKEN", "")
        if not token:
            logger.warning("TUSHARE_TOKEN not set, falling back to mock")
            return MockFinancialBackend()
        try:
            logger.info("[Financial] Using Tushare backend")
            return TushareFinancialBackend(token)
        except Exception as e:
            logger.warning(f"[Financial] Tushare init failed: {e}, using mock")
            return MockFinancialBackend()

    elif api_type == "akshare":
        try:
            import akshare
            logger.info("[Financial] Using AKShare backend (free, no key required)")
            return AKShareFinancialBackend()
        except ImportError:
            logger.warning("AKShare not installed. Run: pip install akshare. Using mock data.")
            return MockFinancialBackend()

    else:
        logger.info("[Financial] Using Mock backend")
        return MockFinancialBackend()
