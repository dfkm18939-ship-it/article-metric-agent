"""
claude/code_reviewer.py
代码审查 Agent — 使用 Claude 3.5 Sonnet 审查生成的 SQL 安全性
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是 SQL 安全审查专家。
请审查 SQL 语句，检查：
1. SQL 注入风险
2. 是否包含危险操作（DROP/DELETE/UPDATE/INSERT）
3. 是否有未过滤的用户输入直接拼接
4. 查询性能问题（缺少索引、全表扫描等）

返回 JSON：{"safe": true/false, "issues": [...], "severity": "low/medium/high"}"""


class CodeReviewer:
    """代码审查 Agent，使用 Claude 3.5 Sonnet"""

    async def review_sql(self, sql: str) -> dict:
        """
        审查 SQL 语句的安全性和质量

        Args:
            sql: 待审查的 SQL 语句

        Returns:
            dict: 审查结果
        """
        prompt = f"待审查的 SQL：\n```sql\n{sql}\n```\n\n请进行安全和质量审查。"
        response = await copilot_client.chat_with_claude(prompt)
        return {"raw": response, "sql": sql}
