"""
Web Search backends — Mock, Serper, Tavily, Brave.

Usage::

    from app.tools.backends.web_search import create_web_search_backend
    backend = create_web_search_backend()
    results = await backend.search("动力电池 行业", top_k=5)
"""

from __future__ import annotations

import json
import os
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any

import httpx

from ...utils.config import get_settings
from ...utils.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Abstract backend
# ═══════════════════════════════════════════════════════════════════════════


class WebSearchBackend(ABC):
    """Abstract interface for web search backends."""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        recency_days: int = 0,
        source_type: str = "",
    ) -> list[dict[str, Any]]:
        """Execute a search and return structured results."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
# Mock backend (built-in data, always available)
# ═══════════════════════════════════════════════════════════════════════════

_MOCK_SEARCH_INDEX: list[dict[str, Any]] = [
    {
        "title": "2025年中国动力电池行业发展现状与竞争格局分析",
        "url": "https://www.eastmoney.com/report/battery_2025",
        "source": "东方财富证券研究",
        "publish_time": "2025-06-15",
        "snippet": "2025年中国动力电池装机量预计突破800GWh，宁德时代以43.2%市场份额稳居第一，比亚迪以27.5%位居第二，行业CR3达到78%。磷酸铁锂占比持续提升至67%。",
        "keywords": ["动力电池", "竞争格局", "市场份额", "宁德时代", "比亚迪"],
    },
    {
        "title": "宁德时代2024年报：营收突破5000亿元，净利润同比增长35%",
        "url": "https://www.catl.com/ir/annual_report_2024",
        "source": "宁德时代官方公告",
        "publish_time": "2025-03-20",
        "snippet": "宁德时代2024年实现营收5230亿元，净利润612亿元，毛利率28.5%，海外收入占比提升至38%。麒麟电池累计装车突破200万辆。",
        "keywords": ["宁德时代", "财报", "营收", "净利润"],
    },
    {
        "title": "工信部：2025年动力电池行业白皮书发布",
        "url": "https://www.miit.gov.cn/whitepaper/battery_2025",
        "source": "工业和信息化部",
        "publish_time": "2025-05-10",
        "snippet": "白皮书指出，2024年中国动力电池产量达950GWh，同比增长42%，行业产值突破1.5万亿元。政策持续支持固态电池等下一代技术研发。",
        "keywords": ["动力电池", "政策", "工信部", "白皮书"],
    },
    {
        "title": "磷酸铁锂VS三元锂：2025年技术路线之争尘埃落定",
        "url": "https://www.36kr.com/article/battery_tech_2025",
        "source": "36氪研究院",
        "publish_time": "2025-04-22",
        "snippet": "磷酸铁锂电池凭借成本优势和安全性能，在乘用车市场份额已达67%。三元锂电池仍占据高端车型和海外市场，两种路线长期共存格局确立。",
        "keywords": ["磷酸铁锂", "三元锂", "技术路线", "动力电池"],
    },
    {
        "title": "动力电池产业链全景图：上游锂资源到下游回收利用",
        "url": "https://www.iresearch.cn/chain/battery_supply_chain",
        "source": "艾瑞咨询",
        "publish_time": "2025-03-01",
        "snippet": "从锂矿、钴镍资源到正极材料、负极材料、电解液、隔膜，再到电芯制造、PACK成组、整车搭载和梯次利用，完整产业链分析。碳酸锂价格回落至12万元/吨。",
        "keywords": ["动力电池", "产业链", "上游", "下游"],
    },
    {
        "title": "比亚迪刀片电池2025年装机量突破150GWh",
        "url": "https://www.autohome.com.cn/news/byd_blade_2025",
        "source": "汽车之家",
        "publish_time": "2025-06-01",
        "snippet": "比亚迪刀片电池2025年累计装机量突破150GWh，搭载车型超过20款。第二代刀片电池能量密度提升至180Wh/kg。",
        "keywords": ["比亚迪", "刀片电池", "装机量"],
    },
    {
        "title": "2025年Q1全球动力电池装机量TOP10排名",
        "url": "https://www.sneresearch.com/global_battery_ranking_q1_2025",
        "source": "SNE Research",
        "publish_time": "2025-05-05",
        "snippet": "全球TOP10中中国企业占6席。宁德时代以36.5%全球份额第一，比亚迪16.8%第二，LG新能源13.2%第三。亿纬锂能首次进入全球前八。",
        "keywords": ["动力电池", "全球排名", "宁德时代", "比亚迪"],
    },
    {
        "title": "固态电池量产在即：2025年动力电池行业最大变数",
        "url": "https://www.cls.cn/tech/solid_state_battery_2025",
        "source": "财联社",
        "publish_time": "2025-06-20",
        "snippet": "宁德时代计划2025年下半年量产半固态电池，能量密度达350Wh/kg。丰田、三星SDI等也在加速布局，全固态电池商业化预计在2027-2028年。",
        "keywords": ["固态电池", "宁德时代", "技术创新"],
    },
    {
        "title": "2025年中国新能源汽车销量预计突破1500万辆",
        "url": "https://www.caam.org.cn/statistics/nev_2025_forecast",
        "source": "中国汽车工业协会",
        "publish_time": "2025-06-10",
        "snippet": "2025年1-5月新能源汽车销量达620万辆，同比增长38%，全年预计突破1500万辆。渗透率突破50%，提前完成2025年目标。",
        "keywords": ["新能源汽车", "销量", "渗透率"],
    },
    {
        "title": "2025年AI算力产业链深度研究：从芯片到数据中心",
        "url": "https://www.guosen.com.cn/report/ai_computing_2025",
        "source": "国信证券研究",
        "publish_time": "2025-05-20",
        "snippet": "2025年中国AI算力市场规模预计达4500亿元，同比增长65%。国产AI芯片市占率提升至18%，华为昇腾、寒武纪成为国产替代主力。",
        "keywords": ["AI算力", "芯片", "数据中心", "国产替代"],
    },
    {
        "title": "英伟达H200/B100供应紧张，国产算力芯片迎来窗口期",
        "url": "https://www.zhitongcaijing.com/ai_chip_shortage_2025",
        "source": "智通财经",
        "publish_time": "2025-06-18",
        "snippet": "受出口管制影响，英伟达高端芯片供应持续紧张，价格溢价30-50%。华为昇腾910B产能爬坡，寒武纪思元590性能达到H100的80%。",
        "keywords": ["AI芯片", "英伟达", "华为", "寒武纪"],
    },
    {
        "title": "2025年低空经济产业政策梳理与市场前景",
        "url": "https://www.caac.gov.cn/policy/low_altitude_2025",
        "source": "中国民用航空局",
        "publish_time": "2025-04-15",
        "snippet": "2025年低空经济首次写入政府工作报告，全国已有28个省份出台低空经济相关政策。eVTOL适航认证取得突破性进展。",
        "keywords": ["低空经济", "eVTOL", "政策", "适航"],
    },
    {
        "title": "中国低空经济市场规模预测：2025-2030年CAGR超40%",
        "url": "https://www.iresearch.cn/low_altitude_economy_market",
        "source": "艾瑞咨询",
        "publish_time": "2025-05-25",
        "snippet": "2025年中国低空经济市场规模预计达1.2万亿元，涵盖无人机物流、空中出行、低空旅游、农业植保等场景。预计2030年突破5万亿元。",
        "keywords": ["低空经济", "市场规模", "CAGR"],
    },
    {
        "title": "2025年白酒行业竞争格局：高端稳、次高端分化、中低端承压",
        "url": "https://www.zhongjin.com/report/baijiu_2025",
        "source": "中金公司研究",
        "publish_time": "2025-06-05",
        "snippet": "2025年茅台批价稳定在2700-2800元，五粮液普五批价980-1020元，国窖1573批价890-920元。行业呈现'一超多强'格局，CR5达45%。",
        "keywords": ["白酒", "竞争格局", "茅台", "五粮液"],
    },
    {
        "title": "贵州茅台2024年报：营收1500亿，增长16%",
        "url": "https://www.moutaichina.com/ir/2024_annual",
        "source": "贵州茅台官方公告",
        "publish_time": "2025-03-30",
        "snippet": "茅台2024年实现营收1503亿元，净利润747亿元，毛利率92.2%，直销占比提升至50%。i茅台平台GMV突破400亿元。",
        "keywords": ["茅台", "年报", "营收", "净利润"],
    },
    {
        "title": "2025年中国光伏产业深度报告：产能过剩与出海突围",
        "url": "https://www.cpia.org.cn/report/solar_2025",
        "source": "中国光伏行业协会",
        "publish_time": "2025-05-15",
        "snippet": "2025年中国光伏新增装机预计250GW，组件价格降至0.7元/W，行业进入产能出清阶段。龙头企业加速海外建厂，东南亚和中东成为新热土。",
        "keywords": ["光伏", "产能", "出海", "组件价格"],
    },
    {
        "title": "隆基绿能、晶澳科技、天合光能2024年业绩对比",
        "url": "https://www.xueqiu.com/analysis/solar_companies_2024",
        "source": "雪球研究",
        "publish_time": "2025-04-20",
        "snippet": "隆基绿能2024年营收1650亿元居首，晶澳科技净利润增速最快达28%，天合光能组件出货量领先。但三家公司毛利率均承压，行业竞争加剧。",
        "keywords": ["光伏", "隆基", "晶澳", "天合", "业绩"],
    },
    {
        "title": "亿纬锂能2024年财报：营收380亿，大圆柱电池量产",
        "url": "https://www.evebattery.com/ir/annual_2024",
        "source": "亿纬锂能官方公告",
        "publish_time": "2025-04-05",
        "snippet": "亿纬锂能2024年营收382亿元，净利润48亿元，同比增长52%。46系大圆柱电池实现量产，宝马、特斯拉为主要客户。储能业务增长120%。",
        "keywords": ["亿纬锂能", "财报", "大圆柱电池"],
    },
    {
        "title": "国轩高科：大众入股后全球化加速，海外营收增长200%",
        "url": "https://www.gotion.com/news/global_2025",
        "source": "国轩高科官方",
        "publish_time": "2025-06-08",
        "snippet": "国轩高科2024年营收282亿元，净利润32亿元。大众汽车集团持股26.5%成为第一大股东，海外市场营收占比提升至35%。",
        "keywords": ["国轩高科", "大众", "全球化"],
    },
    {
        "title": "中创新航：港股上市后首份年报，营收增长65%",
        "url": "https://www.calb-tech.com/ir/2024_annual",
        "source": "中创新航官方公告",
        "publish_time": "2025-03-25",
        "snippet": "中创新航2024年营收256亿元，净利润22亿元，同比增长65%。储能电池出货量增长150%，海外客户拓展至20+国家和地区。",
        "keywords": ["中创新航", "年报", "储能"],
    },
]


class MockSearchBackend(WebSearchBackend):
    """Built-in mock search with 20 realistic Chinese industry results."""

    async def search(
        self, query: str, top_k: int = 5,
        recency_days: int = 0, source_type: str = "",
    ) -> list[dict[str, Any]]:
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        scored = []
        today = datetime.now()

        for item in _MOCK_SEARCH_INDEX:
            text = f"{item['title']} {item['snippet']} {' '.join(item.get('keywords', []))}"
            text_lower = text.lower()
            relevance = len(query_terms & set(text_lower.split())) / max(len(query_terms), 1)
            for term in query_terms:
                if len(term) >= 2 and term in text_lower:
                    relevance += 0.15
            relevance = min(1.0, relevance)
            if relevance <= 0.05:
                continue

            try:
                pub_date = datetime.strptime(item["publish_time"], "%Y-%m-%d")
                freshness = max(0.0, 1.0 - (today - pub_date).days / 365.0)
            except (ValueError, KeyError):
                freshness = 0.5

            if recency_days > 0:
                try:
                    pub_date = datetime.strptime(item["publish_time"], "%Y-%m-%d")
                    if (today - pub_date).days > recency_days:
                        continue
                except (ValueError, KeyError):
                    pass

            if source_type:
                if self._classify_source(item["source"]) != source_type:
                    continue

            scored.append({
                "title": item["title"], "url": item["url"],
                "source": item["source"], "publish_time": item["publish_time"],
                "snippet": item["snippet"],
                "relevance_score": round(relevance, 4),
                "freshness_score": round(freshness, 4),
                "final_score": round(relevance * 0.6 + freshness * 0.4, 4),
            })

        scored.sort(key=lambda x: x["final_score"], reverse=True)
        if len(scored) > top_k and top_k > 1:
            random.seed(hash(query) % 10000)
            random.shuffle(scored[1:top_k])
        return scored[:top_k]

    @staticmethod
    def _classify_source(source: str) -> str:
        if any(k in source for k in ["工信部", "民航局", "海关", "政府"]):
            return "policy"
        if any(k in source for k in ["证券", "中金", "国信", "研究院", "SNE"]):
            return "industry_report"
        if any(k in source for k in ["官方公告", "官网"]):
            return "company_info"
        if any(k in source for k in ["36氪", "财联", "智通", "雪球"]):
            return "news"
        return "analysis"


# ═══════════════════════════════════════════════════════════════════════════
# Serper.dev backend (Google Search API)
# ═══════════════════════════════════════════════════════════════════════════
# API Key 获取: https://serper.dev — 免费额度 2500次/月

SERPER_API_URL = "https://google.serper.dev/search"


class SerperSearchBackend(WebSearchBackend):
    """Real Google search via Serper.dev API."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self, query: str, top_k: int = 5,
        recency_days: int = 0, source_type: str = "",
    ) -> list[dict[str, Any]]:
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload: dict = {"q": query, "num": min(top_k, 10)}

        # Serper doesn't support exact recency filter, but we can add tbs param
        # if recency_days > 0:
        #     payload["tbs"] = f"qdr:d{recency_days}"

        try:
            resp = await self._client.post(SERPER_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            results = []
            today = datetime.now()

            # Organic results
            for i, item in enumerate(data.get("organic", [])[:top_k]):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": self._extract_domain(item.get("link", "")),
                    "publish_time": item.get("date", today.strftime("%Y-%m-%d")),
                    "snippet": item.get("snippet", ""),
                    "relevance_score": round(1.0 - i * 0.1, 4),
                    "freshness_score": 0.8,
                    "final_score": round(0.9 - i * 0.12, 4),
                })

            logger.info(f"[Serper] Query '{query[:50]}...' → {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"[Serper] HTTP {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(f"Serper API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"[Serper] Request failed: {e}")
            raise RuntimeError(f"Serper API request failed: {e}") from e

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL for source display."""
        import re
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return match.group(1) if match else url[:30]


# ═══════════════════════════════════════════════════════════════════════════
# Tavily backend (AI-optimized search API)
# ═══════════════════════════════════════════════════════════════════════════
# API Key 获取: https://tavily.com — 免费额度 1000次/月

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilySearchBackend(WebSearchBackend):
    """Real web search via Tavily API (optimized for AI agents)."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self, query: str, top_k: int = 5,
        recency_days: int = 0, source_type: str = "",
    ) -> list[dict[str, Any]]:
        payload: dict = {
            "api_key": self.api_key,
            "query": query,
            "max_results": min(top_k, 10),
            "search_depth": "advanced",
            "include_answer": False,
        }

        if recency_days > 0:
            payload["days"] = recency_days

        try:
            resp = await self._client.post(TAVILY_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            results = []
            today = datetime.now()

            for i, item in enumerate(data.get("results", [])[:top_k]):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": self._extract_domain(item.get("url", "")),
                    "publish_time": today.strftime("%Y-%m-%d"),
                    "snippet": item.get("content", ""),
                    "relevance_score": round(item.get("score", 0.8), 4),
                    "freshness_score": 0.8,
                    "final_score": round(item.get("score", 0.8), 4),
                })

            logger.info(f"[Tavily] Query '{query[:50]}...' → {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"[Tavily] HTTP {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(f"Tavily API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"[Tavily] Request failed: {e}")
            raise RuntimeError(f"Tavily API request failed: {e}") from e

    @staticmethod
    def _extract_domain(url: str) -> str:
        import re
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return match.group(1) if match else url[:30]


# ═══════════════════════════════════════════════════════════════════════════
# Brave Search backend
# ═══════════════════════════════════════════════════════════════════════════
# API Key 获取: https://brave.com/search/api/ — 免费额度 2000次/月

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchBackend(WebSearchBackend):
    """Real web search via Brave Search API."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self, query: str, top_k: int = 5,
        recency_days: int = 0, source_type: str = "",
    ) -> list[dict[str, Any]]:
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }
        params: dict = {"q": query, "count": min(top_k, 10)}

        try:
            resp = await self._client.get(BRAVE_API_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for i, item in enumerate(data.get("web", {}).get("results", [])[:top_k]):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": self._extract_domain(item.get("url", "")),
                    "publish_time": item.get("age", ""),
                    "snippet": item.get("description", ""),
                    "relevance_score": round(1.0 - i * 0.1, 4),
                    "freshness_score": 0.7,
                    "final_score": round(0.85 - i * 0.12, 4),
                })

            logger.info(f"[Brave] Query '{query[:50]}...' → {len(results)} results")
            return results

        except httpx.HTTPStatusError as e:
            logger.error(f"[Brave] HTTP {e.response.status_code}: {e.response.text[:200]}")
            raise RuntimeError(f"Brave API error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"[Brave] Request failed: {e}")
            raise RuntimeError(f"Brave API request failed: {e}") from e

    @staticmethod
    def _extract_domain(url: str) -> str:
        import re
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return match.group(1) if match else url[:30]


# ═══════════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════════

def create_web_search_backend() -> WebSearchBackend:
    """Create the web search backend based on .env configuration.

    SEARCH_API_TYPE=mock|serper|tavily|brave
    """
    settings = get_settings()
    api_type = settings.SEARCH_API_TYPE.lower()

    if api_type == "serper":
        key = os.getenv("SERPER_API_KEY", "")
        if not key:
            logger.warning("SERPER_API_KEY not set, falling back to mock search")
            return MockSearchBackend()
        logger.info("[WebSearch] Using Serper (Google Search) backend")
        return SerperSearchBackend(key)

    elif api_type == "tavily":
        key = os.getenv("TAVILY_API_KEY", "")
        if not key:
            logger.warning("TAVILY_API_KEY not set, falling back to mock search")
            return MockSearchBackend()
        logger.info("[WebSearch] Using Tavily backend")
        return TavilySearchBackend(key)

    elif api_type == "brave":
        key = os.getenv("BRAVE_API_KEY", "")
        if not key:
            logger.warning("BRAVE_API_KEY not set, falling back to mock search")
            return MockSearchBackend()
        logger.info("[WebSearch] Using Brave Search backend")
        return BraveSearchBackend(key)

    else:
        logger.info("[WebSearch] Using Mock backend (no API key required)")
        return MockSearchBackend()
