"""
gpt/logic_validator.py
业务逻辑校验 Agent — 使用 GPT-4o 检验查询的业务合理性
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是稿件生产指标的业务逻辑专家。
请校验以下查询是否符合业务规则：
1. 时间范围是否合理（不能是未来日期）
2. 指标口径是否存在（签发量/成品量/发布量/退稿量）
3. 维度组合是否合理
4. 数值范围是否符合常规

返回 JSON：{"valid": true/false, "reason": "说明", "suggestions": [...]}"""


class LogicValidator:
    """业务逻辑校验 Agent，使用 GPT-4o"""

    async def validate(self, intent: dict) -> dict:
        """
        校验查询的业务逻辑

        Args:
            intent: IntentAgent 返回的意图结构

        Returns:
            dict: 校验结果
        """
        prompt = f"待校验的查询意图：\n{intent}\n\n请进行业务逻辑校验。"
        response = await copilot_client.chat_with_gpt(prompt, system=_SYSTEM_PROMPT)
        return {"raw": response, "intent": intent}
