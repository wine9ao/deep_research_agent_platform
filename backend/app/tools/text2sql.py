"""Text2SQL Tool — Natural language to SQL with safety validation."""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from .base import BaseTool


# ── SQL Safety Validation ─────────────────────────────────────────────────

FORBIDDEN_SQL_KEYWORDS = [
    "DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "MERGE", "GRANT", "REVOKE", "EXEC",
    "EXECUTE", "ATTACH", "DETACH", "PRAGMA",
]


def validate_sql_safety(sql: str) -> tuple[bool, str]:
    """Validate that a SQL statement only contains safe SELECT operations.

    Args:
        sql: The SQL statement to validate.

    Returns:
        Tuple of (is_safe: bool, reason: str)
    """
    sql_upper = sql.strip().upper()

    # Must start with SELECT or WITH (CTE)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, f"SQL must start with SELECT or WITH, got: {sql[:30]}..."

    # Check for forbidden keywords using word boundary matching
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"Forbidden SQL keyword detected: {keyword}"

    # Check for comment-based injection attempts
    if re.search(r'/\*.*\*/', sql) and len(sql) > 50:
        # Allow simple comments but flag suspicious patterns
        if re.search(r'(?:DROP|DELETE|INSERT|UPDATE|ALTER)\b', sql, re.IGNORECASE):
            return False, "Suspicious SQL comment with forbidden operations detected"

    return True, "OK"


# ── Table schemas ─────────────────────────────────────────────────────────

_TABLE_SCHEMAS = {
    "companies": {
        "columns": ["company_name", "year", "revenue", "net_profit", "gross_margin",
                     "net_margin", "roe", "debt_ratio", "market_share"],
        "description": "公司财务数据表",
    },
    "industries": {
        "columns": ["industry_name", "year", "market_size", "growth_rate",
                     "policy_count", "investment_amount", "penetration_rate"],
        "description": "行业数据表",
    },
}

# ── Query patterns for NL → SQL conversion ────────────────────────────────

_COMPANY_ALIASES: dict[str, str] = {
    "宁德时代": "宁德时代",
    "catl": "宁德时代",
    "比亚迪": "比亚迪",
    "byd": "比亚迪",
    "亿纬锂能": "亿纬锂能",
    "国轩高科": "国轩高科",
    "中创新航": "中创新航",
}

_METRIC_MAP: dict[str, str] = {
    "营收": "revenue", "收入": "revenue", "营业收入": "revenue",
    "净利润": "net_profit", "净利": "net_profit", "利润": "net_profit",
    "毛利率": "gross_margin",
    "净利率": "net_margin",
    "roe": "roe", "净资产收益率": "roe",
    "资产负债率": "debt_ratio", "负债率": "debt_ratio",
    "市场份额": "market_share", "市占率": "market_share", "份额": "market_share",
}

_INDUSTRY_ALIASES: dict[str, str] = {
    "动力电池": "动力电池",
    "新能源汽车": "新能源汽车", "新能源车": "新能源汽车",
    "ai算力": "AI算力", "算力": "AI算力",
    "低空经济": "低空经济",
    "白酒": "白酒",
    "光伏": "光伏", "太阳能": "光伏",
}

_INDUSTRY_METRIC_MAP: dict[str, str] = {
    "市场规模": "market_size", "规模": "market_size",
    "增长率": "growth_rate", "增速": "growth_rate",
    "政策数量": "policy_count", "政策": "policy_count",
    "投资额": "investment_amount", "投资": "investment_amount",
    "渗透率": "penetration_rate",
}


class Text2SQLTool(BaseTool):
    """Convert natural language questions to SQL and execute against SQLite.

    Uses rule-based pattern matching for MVP. Supports Chinese-language
    financial and industry queries with built-in safety validation.

    Only SELECT queries are allowed; all mutation operations are blocked.
    """

    name: str = "text2sql"
    description: str = (
        "自然语言转SQL工具，将中文问题转换为SQL查询并执行。"
        "支持查询公司财务数据和行业指标，内置SQL安全校验。"
    )

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialize with a database path.

        Args:
            db_path: Path to SQLite database. Defaults to in-memory.
        """
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    async def run(self, input: dict) -> dict:
        """Execute a natural language query.

        Args:
            input: dict with keys:
                - question (str): Natural language question
                - db_path (str, optional): Override database path

        Returns:
            dict with success, sql, result, is_safe, and error fields
        """
        try:
            question = input.get("question", "")
            if not question:
                return {"success": False, "sql": "", "result": None, "is_safe": False, "error": "question is required"}

            if "db_path" in input:
                self.db_path = input["db_path"]

            # Step 1: NL → SQL
            sql = self._question_to_sql(question)
            if not sql:
                return {
                    "success": False, "sql": "", "result": None,
                    "is_safe": False,
                    "error": "Could not parse question into SQL. Try a more specific query.",
                }

            # Step 2: Safety validation
            is_safe, reason = validate_sql_safety(sql)
            if not is_safe:
                return {"success": False, "sql": sql, "result": None, "is_safe": False, "error": reason}

            # Step 3: Execute
            result = self._execute_sql(sql)

            return {
                "success": True,
                "sql": sql,
                "result": result,
                "is_safe": True,
                "error": None,
            }
        except Exception as e:
            return {"success": False, "sql": "", "result": None, "is_safe": False, "error": str(e)}

    def _question_to_sql(self, question: str) -> str:
        """Convert a Chinese NL question into a SQL query."""
        question_lower = question.lower().strip()

        # Detect company names
        companies: list[str] = []
        for alias, name in _COMPANY_ALIASES.items():
            if alias.lower() in question_lower:
                if name not in companies:
                    companies.append(name)

        # Detect industry names
        industries: list[str] = []
        for alias, name in _INDUSTRY_ALIASES.items():
            if alias.lower() in question_lower:
                if name not in industries:
                    industries.append(name)

        # Detect metrics
        selected_metrics: list[str] = []
        for cn, en in _METRIC_MAP.items():
            if cn in question and en not in selected_metrics:
                selected_metrics.append(en)
        for cn, en in _INDUSTRY_METRIC_MAP.items():
            if cn in question and en not in selected_metrics:
                selected_metrics.append(en)

        # Detect years
        years = re.findall(r'(\d{4})', question)
        years = [int(y) for y in years if 2018 <= int(y) <= 2030]

        # Detect ordering
        order_col = None
        if "最高" in question or "最大" in question or "排名" in question:
            for cn, en in _METRIC_MAP.items():
                if cn in question:
                    order_col = en
                    break

        # Detect limit
        limit_match = re.search(r'前(\d+)', question)
        limit = int(limit_match.group(1)) if limit_match else 10

        # ── Build SQL ──
        if companies:
            columns = ["company_name", "year"] + (selected_metrics if selected_metrics else ["revenue", "net_profit"])
            cols_str = ", ".join(columns)
            where_clauses = [f"company_name IN ({','.join('?' for _ in companies)})"]
            params = companies.copy()

            if years:
                # "近三年" pattern
                if "近三年" in question or "近3年" in question:
                    recent = max(years) if years else 2025
                    where_clauses.append("year >= ? AND year <= ?")
                    params.extend([recent - 2, recent])
                elif "近两年" in question or "近2年" in question:
                    recent = max(years) if years else 2025
                    where_clauses.append("year >= ? AND year <= ?")
                    params.extend([recent - 1, recent])
                else:
                    where_clauses.append(f"year IN ({','.join('?' for _ in years)})")
                    params.extend([str(y) for y in years])

            sql = f"SELECT {cols_str} FROM companies WHERE {' AND '.join(where_clauses)}"
            if order_col:
                sql += f" ORDER BY {order_col} DESC"
            sql += f" LIMIT {limit}"

            # Substitute parameters directly (safe since params are validated)
            for p in params:
                if isinstance(p, str):
                    sql = sql.replace("?", f"'{p}'", 1)
                else:
                    sql = sql.replace("?", str(p), 1)

        elif industries:
            columns = ["industry_name", "year"] + (selected_metrics if selected_metrics else ["market_size", "growth_rate"])
            cols_str = ", ".join(columns)
            where_clauses = [f"industry_name IN ({','.join('?' for _ in industries)})"]
            params = industries.copy()

            if years:
                where_clauses.append(f"year IN ({','.join('?' for _ in years)})")
                params.extend([str(y) for y in years])

            sql = f"SELECT {cols_str} FROM industries WHERE {' AND '.join(where_clauses)}"
            if order_col:
                sql += f" ORDER BY {order_col} DESC"
            sql += f" LIMIT {limit}"

            for p in params:
                if isinstance(p, str):
                    sql = sql.replace("?", f"'{p}'", 1)
                else:
                    sql = sql.replace("?", str(p), 1)

        else:
            # Generic query - try to figure out table
            if any(kw in question for kw in ["公司", "企业", "营收", "利润", "毛利", "ROE"]):
                sql = "SELECT * FROM companies LIMIT 10"
            elif any(kw in question for kw in ["行业", "市场", "产业"]):
                sql = "SELECT * FROM industries LIMIT 10"
            else:
                return ""

        return sql

    def _execute_sql(self, sql: str) -> list[dict]:
        """Execute a safe SQL query and return results as list of dicts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchall()]
            return rows
        finally:
            conn.close()

    def init_database(self, companies_data: list[dict], industries_data: list[dict]) -> None:
        """Initialize the database with tables and data.

        Args:
            companies_data: List of company financial records.
            industries_data: List of industry records.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    revenue REAL,
                    net_profit REAL,
                    gross_margin REAL,
                    net_margin REAL,
                    roe REAL,
                    debt_ratio REAL,
                    market_share REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS industries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    industry_name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    market_size REAL,
                    growth_rate REAL,
                    policy_count INTEGER,
                    investment_amount REAL,
                    penetration_rate REAL
                )
            """)

            for row in companies_data:
                conn.execute(
                    """INSERT INTO companies
                       (company_name, year, revenue, net_profit, gross_margin,
                        net_margin, roe, debt_ratio, market_share)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["company_name"], row["year"], row.get("revenue"),
                     row.get("net_profit"), row.get("gross_margin"),
                     row.get("net_margin"), row.get("roe"),
                     row.get("debt_ratio"), row.get("market_share")),
                )

            for row in industries_data:
                conn.execute(
                    """INSERT INTO industries
                       (industry_name, year, market_size, growth_rate,
                        policy_count, investment_amount, penetration_rate)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (row["industry_name"], row["year"], row.get("market_size"),
                     row.get("growth_rate"), row.get("policy_count"),
                     row.get("investment_amount"), row.get("penetration_rate")),
                )

            conn.commit()
        finally:
            conn.close()
