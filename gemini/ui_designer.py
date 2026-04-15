"""
gemini/ui_designer.py
UI 方案 Agent — 使用 Gemini 1.5 Pro 生成前端展示方案
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是前端 UI 设计专家，擅长为数据查询结果设计清晰的展示方案。
请根据查询结果设计 HTML/CSS 展示方案：
1. 选择合适的卡片/表格/图表布局
2. 突出关键数值（大字体高亮）
3. 符合新闻媒体行业的专业风格
4. 使用 Tailwind CSS 类名

只返回 HTML 片段，不要包含完整的 HTML 文档结构。"""


class UIDesigner:
    """UI 方案 Agent，使用 Gemini 1.5 Pro"""

    async def design(self, data: list, caliber: str = "签发量") -> str:
        """
        生成数据展示 UI 方案

        Args:
            data: 查询返回的数据列表
            caliber: 指标口径名称

        Returns:
            str: HTML 片段
        """
        prompt = (
            f"指标口径：{caliber}\n"
            f"数据列表：{data}\n\n"
            "请生成对应的 HTML 展示片段。"
        )
        response = await copilot_client.chat_with_gemini(prompt, system=_SYSTEM_PROMPT)
        return response
