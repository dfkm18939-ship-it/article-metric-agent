"""
代码审查 Agent（使用 GitHub Copilot API / Claude 3.5 Sonnet）
负责审查生成的 SQL 语句的安全性和正确性
"""

import json
from core.copilot_client import copilot

CODE_REVIEWER_SYSTEM_PROMPT = """你是一个 SQL 安全审查专家，负责检查 SQL 语句的安全性和正确性。

审查重点：
1. SQL 注入风险
2. 危险操作（DROP/DELETE/TRUNCATE/UPDATE）
3. 语法正确性
4. 性能问题（缺少 LIMIT、全表扫描等）
5. 逻辑正确性

以 JSON 格式返回：
{
  "safe": true|false,
  "issues": ["问题1", "问题2"],
  "severity": "none|low|medium|high|critical",
  "approved_sql": "修正后的 SQL（如有修改）或原 SQL"
}"""


class CodeReviewer:
    """代码审查 Agent，使用 Claude 3.5 Sonnet 进行 SQL 安全审查"""

    async def review(self, sql: str) -> dict:
        """
        审查 SQL 语句

        Args:
            sql: 待审查的 SQL 语句

        Returns:
            包含 safe, issues, severity, approved_sql 字段的审查结果
        """
        prompt = f"请审查以下 SQL 语句：\n\n```sql\n{sql}\n```"
        response = await copilot.chat_with_claude(prompt, system=CODE_REVIEWER_SYSTEM_PROMPT)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            result = json.loads(content)
            # 确保关键字段存在
            result.setdefault("safe", True)
            result.setdefault("issues", [])
            result.setdefault("severity", "none")
            result.setdefault("approved_sql", sql)
            return result
        except json.JSONDecodeError:
            return {
                "safe": True,
                "issues": [],
                "severity": "none",
                "approved_sql": sql,
            }
