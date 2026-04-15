"""
gemini/chart_advisor.py
图表推荐 Agent — 使用 Gemini 1.5 Pro 推荐合适的 ECharts 图表配置
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是数据可视化专家，擅长为不同类型的数据推荐最合适的图表。
请根据数据结构和查询类型推荐 ECharts 图表配置：
1. 选择图表类型（折线图/柱状图/饼图/热力图）
2. 生成 ECharts option 配置（JSON 格式）
3. 设置合理的颜色和样式

只返回 JSON 格式的 ECharts option 配置。"""


class ChartAdvisor:
    """图表推荐 Agent，使用 Gemini 1.5 Pro"""

    async def advise(self, data: list, query_type: str = "trend") -> dict:
        """
        推荐图表配置

        Args:
            data: 查询返回的数据列表
            query_type: 查询类型（trend/compare/distribute）

        Returns:
            dict: ECharts option 配置
        """
        prompt = (
            f"数据列表：{data}\n"
            f"查询类型：{query_type}\n\n"
            "请推荐最合适的 ECharts 图表配置（JSON 格式）。"
        )
        response = await copilot_client.chat_with_gemini(prompt, system=_SYSTEM_PROMPT)
        return {"raw": response, "query_type": query_type}
