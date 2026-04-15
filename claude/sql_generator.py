"""
claude/sql_generator.py
SQL 生成 Agent — 使用 Claude 3.5 Sonnet 将自然语言转换为 SQL
"""

from core.llm_client import copilot_client

_SYSTEM_PROMPT = """你是专业 SQL 工程师，只输出 SQL 代码，不添加任何解释。
数据库表结构：
- articles(id, title, author, dept, column_name, platform, created_at, status)
- article_metrics(article_id, metric_type, metric_value, stat_date)
  metric_type: signed/finished/published/rejected（签发/成品/发布/退稿）

规则：
1. 只生成 SELECT 语句
2. 使用参数化占位符（:param）
3. 包含合理的 WHERE 条件
4. 对聚合查询添加 GROUP BY"""


class SQLGenerator:
    """SQL 生成 Agent，使用 Claude 3.5 Sonnet"""

    async def generate(self, intent: dict) -> str:
        """
        根据查询意图生成 SQL

        Args:
            intent: IntentAgent 返回的意图结构

        Returns:
            str: 生成的 SQL 语句
        """
        prompt = f"查询意图：\n{intent}\n\n请生成对应的 SQL 查询语句。"
        response = await copilot_client.chat_with_claude(
            prompt, system=_SYSTEM_PROMPT
        )
        return response.strip()
