"""
gemini/summary_renderer.py
结果总结 Agent — 使用 Gemini 1.5 Pro 将数据查询结果转为自然语言摘要
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是数据分析报告撰写专家，擅长将数字数据转化为易读的中文摘要。
请根据查询结果生成简洁的分析总结，要求：
1. 突出关键数据点
2. 与历史同期对比（如有）
3. 指出明显趋势
4. 语言简洁，不超过 200 字"""


class SummaryRenderer:
    """结果总结 Agent，使用 Gemini 1.5 Pro"""

    async def render(self, data: list, context: dict = None) -> str:
        """
        生成数据查询结果的文字总结

        Args:
            data: 查询返回的数据列表
            context: 查询上下文

        Returns:
            str: Markdown 格式的总结文本
        """
        prompt = (
            f"查询结果数据：{data}\n"
            f"查询上下文：{context or {}}\n\n"
            "请生成简洁的中文分析总结。"
        )
        response = await copilot_client.chat_with_gemini(prompt, system=_SYSTEM_PROMPT)
        return response
