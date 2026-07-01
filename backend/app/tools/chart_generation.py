"""Chart Generation Tool — Generates ECharts JSON option specifications."""

from __future__ import annotations

from typing import Any

from .base import BaseTool


class ChartGenerationTool(BaseTool):
    """Generate ECharts JSON configuration specs for data visualization.

    Supports line charts, bar charts, pie charts, radar charts,
    horizontal bar charts, and financial trend charts.

    Output is a complete ECharts `option` object that can be directly
    rendered by an ECharts instance in the frontend.
    """

    name: str = "chart_generation"
    description: str = (
        "图表生成工具，支持折线图、柱状图、饼图、雷达图、横向对比图、"
        "财务趋势图等，输出 ECharts JSON spec 供前端渲染。"
    )

    async def run(self, input: dict) -> dict:
        """Generate an ECharts chart specification.

        Args:
            input: dict with keys:
                - chart_type (str): 'line', 'bar', 'pie', 'radar', 'horizontal_bar', 'financial_trend'
                - title (str): Chart title
                - labels (list[str]): X-axis labels or category names
                - series_data (list[dict]): Series data, each with {name, data (list), type}
                  For pie: {name, value}
                - subtitle (str, optional): Chart subtitle
                - height (str, optional): Chart height CSS value
                - colors (list[str], optional): Custom color palette

        Returns:
            dict with success and ECharts option JSON
        """
        try:
            chart_type = input.get("chart_type", "bar")
            title = input.get("title", "图表")
            labels = input.get("labels", [])
            series_data = input.get("series_data", [])
            subtitle = input.get("subtitle", "")
            colors = input.get("colors", [])

            generator_map = {
                "line": self._generate_line_chart,
                "bar": self._generate_bar_chart,
                "pie": self._generate_pie_chart,
                "radar": self._generate_radar_chart,
                "horizontal_bar": self._generate_horizontal_bar_chart,
                "financial_trend": self._generate_financial_trend,
            }

            generator = generator_map.get(chart_type)
            if not generator:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Unsupported chart type: {chart_type}. Supported: {list(generator_map.keys())}",
                }

            option = generator(title, labels, series_data, subtitle, colors)

            return {
                "success": True,
                "data": {
                    "chart_type": chart_type,
                    "title": title,
                    "echarts_option": option,
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    # ── Chart generators ───────────────────────────────────────────────

    def _base_option(self, title: str, subtitle: str = "") -> dict:
        """Create base ECharts option with common styling."""
        option: dict[str, Any] = {
            "title": {
                "text": title,
                "subtext": subtitle,
                "left": "center",
                "textStyle": {"fontSize": 16, "fontWeight": "bold"},
            },
            "tooltip": {"trigger": "axis" if True else "item"},
            "legend": {
                "orient": "horizontal",
                "bottom": 0,
                "textStyle": {"fontSize": 12},
            },
            "grid": {
                "left": "3%",
                "right": "4%",
                "bottom": "15%",
                "containLabel": True,
            },
            "color": [
                "#5470C6", "#91CC75", "#FAC858", "#EE6666",
                "#73C0DE", "#3BA272", "#FC8452", "#9A60B4",
            ],
        }
        return option

    def _generate_line_chart(
        self, title: str, labels: list[str], series_data: list[dict],
        subtitle: str, colors: list[str]
    ) -> dict:
        """Generate a line chart ECharts option."""
        option = self._base_option(title, subtitle)
        option["tooltip"]["trigger"] = "axis"
        option["xAxis"] = {
            "type": "category",
            "data": labels,
            "axisLabel": {"rotate": labels and len(labels) > 6 and 30 or 0},
        }
        option["yAxis"] = {"type": "value", "name": ""}
        option["series"] = [
            {
                "name": s.get("name", f"系列{i + 1}"),
                "type": "line",
                "data": s.get("data", []),
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 6,
            }
            for i, s in enumerate(series_data)
        ]
        if colors:
            option["color"] = colors
        return option

    def _generate_bar_chart(
        self, title: str, labels: list[str], series_data: list[dict],
        subtitle: str, colors: list[str]
    ) -> dict:
        """Generate a bar chart ECharts option."""
        option = self._base_option(title, subtitle)
        option["tooltip"]["trigger"] = "axis"
        option["xAxis"] = {
            "type": "category",
            "data": labels,
            "axisLabel": {"rotate": labels and len(labels) > 5 and 30 or 0},
        }
        option["yAxis"] = {"type": "value", "name": ""}
        option["series"] = [
            {
                "name": s.get("name", f"系列{i + 1}"),
                "type": "bar",
                "data": s.get("data", []),
                "barMaxWidth": 50,
                "itemStyle": {"borderRadius": [4, 4, 0, 0]},
            }
            for i, s in enumerate(series_data)
        ]
        if len(series_data) > 1:
            # Make bars side by side for multi-series
            for s in option["series"]:
                s["barGap"] = "10%"
        if colors:
            option["color"] = colors
        return option

    def _generate_pie_chart(
        self, title: str, labels: list[str], series_data: list[dict],
        subtitle: str, colors: list[str]
    ) -> dict:
        """Generate a pie chart ECharts option."""
        option = self._base_option(title, subtitle)
        option["tooltip"]["trigger"] = "item"
        option["tooltip"]["formatter"] = "{b}: {c} ({d}%)"

        pie_data = []
        for i, s in enumerate(series_data):
            if "name" in s and "value" in s:
                pie_data.append({"name": s["name"], "value": s["value"]})
            elif "data" in s:
                # data is list of values mapped to labels
                for j, val in enumerate(s["data"]):
                    label = labels[j] if j < len(labels) else f"项目{j + 1}"
                    pie_data.append({"name": label, "value": val})

        option["series"] = [{
            "name": title,
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "55%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 6,
                "borderColor": "#fff",
                "borderWidth": 2,
            },
            "label": {
                "show": True,
                "formatter": "{b}: {d}%",
            },
            "emphasis": {
                "label": {"show": True, "fontSize": 16, "fontWeight": "bold"},
            },
            "data": pie_data,
        }]
        if colors:
            option["color"] = colors
        return option

    def _generate_radar_chart(
        self, title: str, labels: list[str], series_data: list[dict],
        subtitle: str, colors: list[str]
    ) -> dict:
        """Generate a radar chart ECharts option."""
        option = self._base_option(title, subtitle)
        option["tooltip"]["trigger"] = "item"
        option.pop("grid", None)

        indicator = [{"name": label, "max": 100} for label in labels]

        option["radar"] = {
            "indicator": indicator,
            "center": ["50%", "55%"],
            "radius": "65%",
        }
        option["series"] = [{
            "type": "radar",
            "data": [
                {
                    "name": s.get("name", f"系列{i + 1}"),
                    "value": s.get("data", []),
                }
                for i, s in enumerate(series_data)
            ],
            "areaStyle": {"opacity": 0.3},
        }]
        if colors:
            option["color"] = colors
        return option

    def _generate_horizontal_bar_chart(
        self, title: str, labels: list[str], series_data: list[dict],
        subtitle: str, colors: list[str]
    ) -> dict:
        """Generate a horizontal bar chart ECharts option."""
        option = self._base_option(title, subtitle)
        option["tooltip"]["trigger"] = "axis"
        option["yAxis"] = {
            "type": "category",
            "data": labels,
            "inverse": True,
        }
        option["xAxis"] = {"type": "value", "name": ""}
        option["series"] = [
            {
                "name": s.get("name", f"系列{i + 1}"),
                "type": "bar",
                "data": s.get("data", []),
                "barMaxWidth": 30,
                "itemStyle": {"borderRadius": [0, 4, 4, 0]},
            }
            for i, s in enumerate(series_data)
        ]
        if colors:
            option["color"] = colors
        return option

    def _generate_financial_trend(
        self, title: str, labels: list[str], series_data: list[dict],
        subtitle: str, colors: list[str]
    ) -> dict:
        """Generate a financial trend chart (dual axis line + bar)."""
        option = self._base_option(title, subtitle)
        option["tooltip"]["trigger"] = "axis"
        option["xAxis"] = {"type": "category", "data": labels}
        option["yAxis"] = [
            {"type": "value", "name": series_data[0].get("yAxisName", "金额(亿元)") if series_data else ""},
            {"type": "value", "name": series_data[1].get("yAxisName", "增长率(%)") if len(series_data) > 1 else ""},
        ]
        option["series"] = []
        for i, s in enumerate(series_data):
            series_item = {
                "name": s.get("name", f"系列{i + 1}"),
                "type": s.get("type", "bar" if i == 0 else "line"),
                "data": s.get("data", []),
                "yAxisIndex": i if i < 2 else 0,
            }
            if series_item["type"] == "bar":
                series_item["barMaxWidth"] = 50
                series_item["itemStyle"] = {"borderRadius": [4, 4, 0, 0]}
            else:
                series_item["smooth"] = True
                series_item["symbol"] = "circle"
                series_item["symbolSize"] = 8
            option["series"].append(series_item)

        if colors:
            option["color"] = colors
        return option
