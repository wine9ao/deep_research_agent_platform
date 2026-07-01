"""Data Analysis Tool — Statistical analysis on structured financial/industry data."""

from __future__ import annotations

from typing import Any

from .base import BaseTool


class DataAnalysisTool(BaseTool):
    """Analyze structured data and produce insights in Chinese.

    Supports year-over-year growth (YoY), CAGR, ranking, percentage
    calculations, and summary statistics. Returns both tabular data
    and natural-language insights.
    """

    name: str = "data_analysis"
    description: str = (
        "数据分析工具，支持同比、环比、CAGR、占比、排名、汇总统计等分析，"
        "返回结构化表格和中文自然语言洞察。"
    )

    async def run(self, input: dict) -> dict:
        """Run data analysis operations.

        Args:
            input: dict with keys:
                - operation (str): One of 'yoy_growth', 'cagr', 'ranking',
                  'summary_stats', 'percentage', 'comparison'
                - data (list[dict]): List of data records
                - value_column (str): Column to analyze
                - group_column (str, optional): Column to group by
                - year_column (str, optional): Year column for time-based analysis

        Returns:
            dict with success, data (table + insights), error
        """
        try:
            operation = input.get("operation", "summary_stats")
            data = input.get("data", [])
            value_column = input.get("value_column", "value")
            group_column = input.get("group_column", "")
            year_column = input.get("year_column", "year")

            if not data:
                return {"success": False, "data": None, "error": "data is required"}

            if operation == "summary_stats":
                result = self._summary_stats(data, value_column)
            elif operation == "yoy_growth":
                result = self._yoy_growth(data, value_column, group_column, year_column)
            elif operation == "cagr":
                result = self._cagr(data, value_column, group_column, year_column)
            elif operation == "ranking":
                result = self._ranking(data, value_column, group_column)
            elif operation == "percentage":
                result = self._percentage(data, value_column, group_column)
            elif operation == "comparison":
                result = self._comparison(data, value_column, group_column, year_column)
            else:
                return {"success": False, "data": None, "error": f"Unknown operation: {operation}"}

            return {"success": True, "data": result, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    # ── Analysis methods ───────────────────────────────────────────────

    def _summary_stats(self, data: list[dict], value_col: str) -> dict:
        """Compute summary statistics."""
        values = [r[value_col] for r in data if value_col in r]
        if not values:
            return {"table": [], "insights": ["无有效数据"]}

        n = len(values)
        mean_val = sum(values) / n
        sorted_vals = sorted(values)
        median_val = sorted_vals[n // 2]
        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]
        std_val = (sum((v - mean_val) ** 2 for v in values) / n) ** 0.5

        table = [
            {"指标": "样本数", "值": n},
            {"指标": "均值", "值": round(mean_val, 2)},
            {"指标": "中位数", "值": round(median_val, 2)},
            {"指标": "最小值", "值": round(min_val, 2)},
            {"指标": "最大值", "值": round(max_val, 2)},
            {"指标": "标准差", "值": round(std_val, 2)},
            {"指标": "变异系数", "值": f"{round(std_val / mean_val * 100, 1)}%" if mean_val else "N/A"},
        ]

        insights = [
            f"共分析{n}条数据记录。",
            f"平均值为{round(mean_val, 2)}，中位数为{round(median_val, 2)}。",
            f"数据范围从{round(min_val, 2)}到{round(max_val, 2)}，极差为{round(max_val - min_val, 2)}。",
        ]
        if std_val / max(mean_val, 0.001) > 0.3:
            insights.append("数据离散程度较高，存在显著个体差异。")

        return {"table": table, "insights": insights}

    def _yoy_growth(
        self, data: list[dict], value_col: str, group_col: str, year_col: str
    ) -> dict:
        """Compute year-over-year growth rates."""
        # Group by group_col, sort by year
        groups: dict[str, dict[int, float]] = {}
        for r in data:
            group = r.get(group_col, "default")
            year = r.get(year_col, 0)
            value = r.get(value_col, 0)
            if group not in groups:
                groups[group] = {}
            groups[group][year] = value

        table = []
        for group, year_data in groups.items():
            sorted_years = sorted(year_data.keys())
            for i in range(1, len(sorted_years)):
                prev_year = sorted_years[i - 1]
                curr_year = sorted_years[i]
                prev_val = year_data[prev_year]
                curr_val = year_data[curr_year]
                if prev_val:
                    growth = (curr_val - prev_val) / prev_val
                    table.append({
                        "分组": group,
                        "年份": curr_year,
                        "上一年": prev_year,
                        "当前值": round(curr_val, 2),
                        "上期值": round(prev_val, 2),
                        "同比增长率": f"{round(growth * 100, 1)}%",
                    })

        avg_growths = []
        for row in table:
            try:
                avg_growths.append(float(row["同比增长率"].replace("%", "")))
            except (ValueError, KeyError):
                pass
        avg_growth = sum(avg_growths) / len(avg_growths) if avg_growths else 0

        insights = [
            f"共计算{table.__len__()}条同比增长率。",
            f"平均同比增长率为{round(avg_growth, 1)}%。",
        ]
        if avg_growth > 20:
            insights.append("整体增长势头强劲，行业处于快速发展期。")
        elif avg_growth > 5:
            insights.append("整体增长稳健，行业处于成熟发展期。")
        else:
            insights.append("整体增长放缓，可能进入调整阶段。")

        return {"table": table, "insights": insights}

    def _cagr(
        self, data: list[dict], value_col: str, group_col: str, year_col: str
    ) -> dict:
        """Compute Compound Annual Growth Rate."""
        groups: dict[str, dict[int, float]] = {}
        for r in data:
            group = r.get(group_col, "default")
            year = r.get(year_col, 0)
            value = r.get(value_col, 0)
            if group not in groups:
                groups[group] = {}
            groups[group][year] = value

        table = []
        for group, year_data in groups.items():
            sorted_years = sorted(year_data.keys())
            if len(sorted_years) < 2:
                continue
            first_year = sorted_years[0]
            last_year = sorted_years[-1]
            first_val = year_data[first_year]
            last_val = year_data[last_year]
            n = last_year - first_year
            if first_val > 0 and n > 0:
                cagr_val = ((last_val / first_val) ** (1 / n) - 1) * 100
                table.append({
                    "分组": group,
                    "起始年": first_year,
                    "结束年": last_year,
                    "起始值": round(first_val, 2),
                    "结束值": round(last_val, 2),
                    "年数": n,
                    "CAGR": f"{round(cagr_val, 1)}%",
                })

        insights = [f"共计算{table.__len__()}组CAGR。"]
        if table:
            highest = max(table, key=lambda x: float(x["CAGR"].replace("%", "")))
            insights.append(f"CAGR最高的分组为「{highest['分组']}」，达{highest['CAGR']}。")

        return {"table": table, "insights": insights}

    def _ranking(self, data: list[dict], value_col: str, group_col: str) -> dict:
        """Rank groups by a metric."""
        if group_col:
            groups: dict[str, float] = {}
            for r in data:
                group = r[group_col]
                value = r.get(value_col, 0)
                groups[group] = max(groups.get(group, float("-inf")), value)
            sorted_groups = sorted(groups.items(), key=lambda x: x[1], reverse=True)
            table = [
                {"排名": i + 1, "分组": g, "值": round(v, 2)}
                for i, (g, v) in enumerate(sorted_groups)
            ]
        else:
            sorted_data = sorted(data, key=lambda x: x.get(value_col, 0), reverse=True)
            table = [
                {"排名": i + 1, **{k: v for k, v in r.items()}}
                for i, r in enumerate(sorted_data)
            ]

        insights = []
        if len(table) >= 3:
            insights.append(f"排名第一的是「{table[0].get('分组', table[0])}」。")
            insights.append(f"前三名分别是：{', '.join(str(r.get('分组', '')) for r in table[:3])}。")

        return {"table": table, "insights": insights}

    def _percentage(self, data: list[dict], value_col: str, group_col: str) -> dict:
        """Calculate percentage of each group."""
        if not group_col:
            return {"table": [], "insights": ["需要指定分组列进行计算。"]}

        total = sum(r.get(value_col, 0) for r in data)
        if total == 0:
            return {"table": [], "insights": ["总值为零，无法计算占比。"]}

        groups: dict[str, float] = {}
        for r in data:
            group = r[group_col]
            groups[group] = groups.get(group, 0) + r.get(value_col, 0)

        table = [
            {"分组": g, "值": round(v, 2), "占比": f"{round(v / total * 100, 1)}%"}
            for g, v in sorted(groups.items(), key=lambda x: x[1], reverse=True)
        ]

        insights = [
            f"总值为{round(total, 2)}。",
            f"占比最高的是「{table[0]['分组']}」，达{table[0]['占比']}。",
        ]
        if len(table) >= 2:
            top2 = float(table[0]["占比"].replace("%", "")) + float(table[1]["占比"].replace("%", ""))
            insights.append(f"前两名合计占比{round(top2, 1)}%。")

        return {"table": table, "insights": insights}

    def _comparison(
        self, data: list[dict], value_col: str, group_col: str, year_col: str
    ) -> dict:
        """Compare multiple groups across years."""
        groups: dict[str, dict[int, float]] = {}
        for r in data:
            group = r.get(group_col, "default")
            year = r.get(year_col, 0)
            value = r.get(value_col, 0)
            if group not in groups:
                groups[group] = {}
            groups[group][year] = value

        all_years = sorted(set(y for gd in groups.values() for y in gd))
        table = []
        for group, year_data in groups.items():
            row: dict = {"分组": group}
            for y in all_years:
                row[str(y)] = round(year_data.get(y, 0), 2)
            table.append(row)

        insights = [f"对比{table.__len__()}个分组在{len(all_years)}个年份的表现。"]
        if len(groups) >= 2:
            group_names = list(groups.keys())
            insights.append(f"共对比{len(group_names)}个主体：{'、'.join(group_names[:5])}。")

        return {"table": table, "insights": insights}
