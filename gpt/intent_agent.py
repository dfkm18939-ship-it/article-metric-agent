"""
gpt/intent_agent.py
意图识别 Agent — 使用 GPT-4o 理解用户查询意图
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是一个稿件指标查询系统的意图识别专家。
请分析用户的查询，提取：
1. 查询类型（签发量/成品量/发布量/退稿量/等）
2. 时间范围（年/月/日/自定义区间）
3. 过滤维度（部门/记者/栏目/平台）
4. 聚合方式（汇总/分组/趋势）

以 JSON 格式返回结果。"""


class IntentAgent:
    """意图识别 Agent，使用 GPT-4o"""

    async def recognize(self, user_query: str) -> dict:
        """
        识别用户查询意图

        Args:
            user_query: 用户原始查询文本

        Returns:
            dict: 包含意图信息的结构化结果
        """
        prompt = f"用户查询：{user_query}\n\n请分析查询意图并以 JSON 格式返回。"
        response = await copilot_client.chat_with_gpt(prompt, system=_SYSTEM_PROMPT)
        return {"raw": response, "query": user_query}
