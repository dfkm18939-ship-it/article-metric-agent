"""
gpt/anomaly_analyzer.py
异常分析 Agent — 使用 GPT-4o 检测数据异常并给出解释
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是稿件生产数据的异常分析专家。
请检测查询结果中的异常情况：
1. 数值突增/突降（超过均值 ±3σ）
2. 与同期对比异常
3. 逻辑矛盾（如成品量 > 签发量）
4. 数据缺失或不完整

返回 JSON：{"has_anomaly": true/false, "anomalies": [...], "explanation": "..."}"""


class AnomalyAnalyzer:
    """异常分析 Agent，使用 GPT-4o"""

    async def analyze(self, data: list, context: dict = None) -> dict:
        """
        分析数据异常

        Args:
            data: 查询返回的数据列表
            context: 查询上下文（时间范围、指标类型等）

        Returns:
            dict: 异常分析结果
        """
        prompt = (
            f"数据列表：{data}\n"
            f"查询上下文：{context or {}}\n\n"
            "请进行异常检测分析。"
        )
        response = await copilot_client.chat_with_gpt(prompt, system=_SYSTEM_PROMPT)
        return {"raw": response, "data_count": len(data)}
