# gemini/chart_advisor.py
# 职责：根据数据结构推荐图表类型和 ECharts 配置
# 模型：Gemini

import json
import logging

from core.llm_client import GeminiClient

logger = logging.getLogger(__name__)

_SYSTEM = """你是数据可视化专家，根据数据结构推荐最合适的图表类型并生成 ECharts option 配置。
只返回 JSON，不要任何额外内容。"""


class ChartAdvisor:
    """图表类型推荐（Gemini）"""

    def __init__(self):
        self.llm = GeminiClient()

    def run(self, data: list[dict], dimension: str | None = None) -> dict:
        """
        返回：{chart_type: str, echarts_option: dict, description: str}
        """
        if not data:
            return self._empty_chart()

        # 本地判断图表类型
        chart_type = self._infer_type(data, dimension)

        if chart_type == "card":
            return self._card_chart(data)

        # 复杂图表由 Gemini 生成
        prompt = f"""
数据：{json.dumps(data, ensure_ascii=False)}
维度字段：{dimension}
推荐图表类型：{chart_type}

请为上述数据生成完整的 ECharts option JSON 配置。
- 折线图（line）：xAxis 为时间，yAxis 为数量，series 为签发量
- 柱状图（bar）：xAxis 为维度值，yAxis 为数量，series 为签发量
- 颜色使用 #4096ff（蓝色主题）
- 图表标题使用 "稿件签发通过量"
- tooltip 显示数量和单位"篇"

只返回 JSON：
{{
  "chart_type": "{chart_type}",
  "echarts_option": {{ ... ECharts option 完整对象 ... }},
  "description": "图表说明"
}}
"""
        raw = self.llm.chat(prompt, system=_SYSTEM)
        result = self._parse_json(raw)

        if not result.get("echarts_option"):
            result = self._fallback_chart(data, chart_type, dimension)

        return result

    # ── 类型推断 ──────────────────────────────────────────────

    @staticmethod
    def _infer_type(data: list[dict], dimension: str | None) -> str:
        if len(data) == 1 and not dimension:
            return "card"
        # 如果有时间字段，用折线图
        first = data[0] if data else {}
        for key in first:
            if any(t in key.lower() for t in ("date", "time", "month", "week", "day")):
                return "line"
        return "bar"

    @staticmethod
    def _card_chart(data: list[dict]) -> dict:
        value = 0
        if data:
            first = data[0]
            for key in ("signed_count", "count", "total", "value"):
                if key in first:
                    value = first[key] or 0
                    break
        return {
            "chart_type": "card",
            "echarts_option": {},
            "card_value": value,
            "card_unit": "篇",
            "description": f"签发通过 {value} 篇",
        }

    @staticmethod
    def _empty_chart() -> dict:
        return {
            "chart_type": "card",
            "echarts_option": {},
            "card_value": 0,
            "card_unit": "篇",
            "description": "暂无数据",
        }

    @staticmethod
    def _fallback_chart(data: list[dict], chart_type: str, dimension: str | None) -> dict:
        """Gemini 失败时的降级图表配置"""
        if not data:
            return ChartAdvisor._empty_chart()
        keys = list(data[0].keys())
        x_key = keys[0] if len(keys) > 1 else keys[0]
        y_key = keys[1] if len(keys) > 1 else keys[0]
        x_data = [str(row.get(x_key, "")) for row in data]
        y_data = [row.get(y_key, 0) for row in data]
        option = {
            "title": {"text": "稿件签发通过量"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data},
            "yAxis": {"type": "value"},
            "series": [{"type": chart_type, "data": y_data, "itemStyle": {"color": "#4096ff"}}],
        }
        return {
            "chart_type": chart_type,
            "echarts_option": option,
            "description": f"{chart_type} 图表",
        }

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("`").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("ChartAdvisor JSON parse error: %s", e)
            return {}
