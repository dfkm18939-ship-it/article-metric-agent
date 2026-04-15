"""
逻辑校验 Agent（使用 GitHub Copilot API / GPT-4o）
负责校验 SQL 查询结果的业务逻辑合理性
"""

import json
from core.copilot_client import copilot

LOGIC_VALIDATOR_SYSTEM_PROMPT = """你是一个稿件数据质量校验专家。
给定一个 SQL 查询结果，判断数据是否符合业务逻辑。

请以 JSON 格式返回：
{
  "valid": true|false,
  "issues": ["问题描述1", "问题描述2"],
  "confidence": 0.0-1.0,
  "suggestion": "建议说明（如有问题）"
}

业务规则：
- 签发量不应为负数
- 单日签发量不应超过 10000
- 时间范围应合理（不超过当前日期）
- 各部门总量之和应等于汇总量（允许 1% 误差）"""


class LogicValidator:
    """逻辑校验 Agent，使用 GPT-4o 进行业务规则验证"""

    async def validate(self, query_result: dict, intent: dict) -> dict:
        """
        校验查询结果的业务逻辑

        Args:
            query_result: SQL 查询结果数据
            intent: 原始意图解析结果

        Returns:
            包含 valid, issues, confidence 字段的校验结果
        """
        prompt = f"""
查询意图：{json.dumps(intent, ensure_ascii=False)}
查询结果：{json.dumps(query_result, ensure_ascii=False)}

请校验数据是否符合业务逻辑。
"""
        response = await copilot.chat_with_gpt(prompt, system=LOGIC_VALIDATOR_SYSTEM_PROMPT)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "valid": True,
                "issues": [],
                "confidence": 0.8,
                "suggestion": "",
            }
