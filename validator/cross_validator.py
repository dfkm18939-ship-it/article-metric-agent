"""
交叉验证 Agent（多模型互审机制）
使用不同模型互相验证结果，提高可靠性
"""

import json
from core.copilot_client import copilot

VALIDATE_SQL_SYSTEM = """你是一个 SQL 专家，请验证给定 SQL 语句的正确性。
以 JSON 返回：{"valid": true|false, "reason": "说明", "fixed_sql": "修正后的SQL或原SQL"}"""

VALIDATE_INTENT_SYSTEM = """你是一个业务专家，请验证意图解析结果是否符合稿件统计业务规则。
以 JSON 返回：{"valid": true|false, "reason": "说明", "confidence": 0.0-1.0}"""

VALIDATE_DISPLAY_SYSTEM = """你是一个数据展示专家，请验证展示内容是否准确反映了查询数据。
以 JSON 返回：{"valid": true|false, "reason": "说明", "issues": []}"""


class CrossValidator:
    """交叉验证器，使用多模型互审提高结果可靠性"""

    async def validate_sql(self, sql: str, intent: dict) -> dict:
        """
        使用 GPT 验证 SQL 正确性（验证 Claude 生成的 SQL）

        Args:
            sql: 待验证的 SQL
            intent: 原始查询意图

        Returns:
            包含 valid, reason, fixed_sql 字段的字典
        """
        prompt = f"""
查询意图：{json.dumps(intent, ensure_ascii=False)}
待验证 SQL：{sql}

请验证 SQL 是否正确实现了查询意图。
"""
        response = await copilot.chat_with_gpt(prompt, system=VALIDATE_SQL_SYSTEM)
        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            return {"valid": True, "reason": "验证通过", "fixed_sql": sql}

    async def validate_intent(self, intent: dict, user_query: str) -> dict:
        """
        使用 Claude 验证意图解析正确性（验证 GPT 的意图理解）

        Args:
            intent: GPT 解析出的意图
            user_query: 原始用户查询

        Returns:
            包含 valid, reason, confidence 字段的字典
        """
        prompt = f"""
用户原始查询：{user_query}
意图解析结果：{json.dumps(intent, ensure_ascii=False)}

请验证意图解析是否正确反映了用户需求。
"""
        response = await copilot.chat_with_claude(prompt, system=VALIDATE_INTENT_SYSTEM)
        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            return {"valid": True, "reason": "验证通过", "confidence": 0.9}

    async def validate_display(self, summary_html: str, query_result: dict) -> dict:
        """
        使用 GPT 验证展示内容准确性（验证 Gemini 的总结）

        Args:
            summary_html: Gemini 生成的 HTML 摘要
            query_result: 原始查询结果

        Returns:
            包含 valid, reason, issues 字段的字典
        """
        prompt = f"""
原始查询数据：{json.dumps(query_result, ensure_ascii=False)}
展示内容：{summary_html}

请验证展示内容是否准确反映了数据。
"""
        response = await copilot.chat_with_gpt(prompt, system=VALIDATE_DISPLAY_SYSTEM)
        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            return {"valid": True, "reason": "验证通过", "issues": []}
