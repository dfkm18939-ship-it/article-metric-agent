# gemini/chart_advisor.py — 图表类型推荐，返回 ECharts 配置 JSON（Gemini）

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChartAdvisor:
    """图表类型推荐与 ECharts 配置生成（Gemini 负责）"""

    def recommend(self, data: list[dict], intent: dict) -> dict[str, Any]:
        """
        根据数据结构和意图推荐图表配置。
        返回 {type, title, echarts_option}
        """
        if not data:
            return self._stat_card(0, intent)

        dimension = intent.get("dimension")
        time_expr = intent.get("time_expression", "今年")
        metric_name = intent.get("metric_name", "签发量")

        # 单一数值（无维度）
        if len(data) == 1 and not dimension:
            value = list(data[0].values())[0]
            return self._stat_card(value, intent)

        # 时间维度 → 折线图
        time_dims = ["日", "周", "月", "年"]
        time_fields = {"DATE(signed_at)", "strftime('%Y-%W', signed_at)",
                       "strftime('%Y-%m', signed_at)", "strftime('%Y', signed_at)"}
        keys = list(data[0].keys()) if data else []
        has_time_dim = any(f in str(keys) for f in ["date", "month", "week", "year", "signed_at"])

        if dimension in (None, "") and len(data) > 1:
            return self._line_chart(data, metric_name, time_expr)

        # 业务维度对比 → 柱状图
        if dimension in ("dept_name", "article_type", "author_name", "column_name"):
            return self._bar_chart(data, dimension, metric_name)

        # 默认：柱状图
        return self._bar_chart(data, dimension or "维度", metric_name)

    def _stat_card(self, value: Any, intent: dict) -> dict[str, Any]:
        metric_name = intent.get("metric_name", "签发量")
        time_expr = intent.get("time_expression", "今年")
        return {
            "type": "stat_card",
            "title": f"{time_expr}{metric_name}",
            "value": value,
            "unit": "篇",
            "echarts_option": None,
        }

    def _line_chart(self, data: list[dict], metric_name: str, time_expr: str) -> dict[str, Any]:
        keys = list(data[0].keys())
        x_key = keys[0]
        y_key = keys[-1]
        x_data = [str(row.get(x_key, "")) for row in data]
        y_data = [row.get(y_key, 0) for row in data]

        option = {
            "title": {"text": f"{time_expr}{metric_name}趋势"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data},
            "yAxis": {"type": "value", "name": "篇"},
            "series": [{
                "name": metric_name,
                "type": "line",
                "data": y_data,
                "smooth": True,
                "areaStyle": {"opacity": 0.1},
                "itemStyle": {"color": "#1a73e8"},
            }],
        }
        return {"type": "line", "title": f"{time_expr}{metric_name}趋势", "echarts_option": option}

    def _bar_chart(self, data: list[dict], dimension: str, metric_name: str) -> dict[str, Any]:
        keys = list(data[0].keys())
        x_key = keys[0]
        y_key = keys[-1]
        x_data = [str(row.get(x_key, "")) for row in data]
        y_data = [row.get(y_key, 0) for row in data]

        dim_label_map = {
            "dept_name": "部门",
            "article_type": "稿件类型",
            "author_name": "作者",
            "column_name": "栏目",
        }
        dim_label = dim_label_map.get(dimension, dimension)

        option = {
            "title": {"text": f"各{dim_label}{metric_name}对比"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data, "axisLabel": {"rotate": 30}},
            "yAxis": {"type": "value", "name": "篇"},
            "series": [{
                "name": metric_name,
                "type": "bar",
                "data": y_data,
                "itemStyle": {"color": "#1a73e8"},
                "label": {"show": True, "position": "top"},
            }],
        }
        return {"type": "bar", "title": f"各{dim_label}{metric_name}对比", "echarts_option": option}
