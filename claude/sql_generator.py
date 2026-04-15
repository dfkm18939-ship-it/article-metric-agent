"""
SQL 生成 Agent（使用 GitHub Copilot API / Claude 3.5 Sonnet）
负责将结构化意图转化为精确的 SQL 查询语句
"""

import json
from core.copilot_client import copilot

SQL_GENERATOR_SYSTEM_PROMPT = """你是一个专业的 SQL 生成专家，擅长为稿件指标系统生成精确的 SQLite 查询。

数据库表结构：
CREATE TABLE articles (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    author      TEXT,
    department  TEXT,
    category    TEXT,
    status      TEXT,          -- draft/reviewing/approved/published/rejected
    created_at  DATE,
    approved_at DATE,          -- 签发日期
    published_at DATE,         -- 发布日期
    word_count  INTEGER,
    views       INTEGER DEFAULT 0
);

口径定义：
- 签发量：status='approved' AND approved_at 在时间范围内
- 发布量：status='published' AND published_at 在时间范围内
- 审核通过量：status IN ('approved','published') AND approved_at 在时间范围内

请生成标准 SQLite 语法的 SQL，返回格式：
{
  "sql": "SELECT ...",
  "explanation": "SQL 说明"
}

只返回 JSON，不要添加任何解释。"""


class SQLGenerator:
    """SQL 生成 Agent，使用 Claude 3.5 Sonnet"""

    async def generate(self, intent: dict) -> dict:
        """
        根据意图生成 SQL 查询

        Args:
            intent: IntentAgent 解析出的意图字典

        Returns:
            包含 sql 和 explanation 字段的字典
        """
        prompt = f"查询意图：{json.dumps(intent, ensure_ascii=False)}\n\n请生成对应的 SQL 查询。"
        response = await copilot.chat_with_claude(prompt, system=SQL_GENERATOR_SYSTEM_PROMPT)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            # 生成一个默认查询
            caliber = intent.get("caliber", "签发量")
            time_range = intent.get("time_range", {})
            start = time_range.get("start", "2024-01-01")
            end = time_range.get("end", "2024-12-31")

            if caliber == "签发量":
                where = f"status = 'approved' AND approved_at BETWEEN '{start}' AND '{end}'"
            elif caliber == "发布量":
                where = f"status = 'published' AND published_at BETWEEN '{start}' AND '{end}'"
            else:
                where = f"status IN ('approved','published') AND approved_at BETWEEN '{start}' AND '{end}'"

            sql = f"SELECT COUNT(*) AS total FROM articles WHERE {where};"
            return {"sql": sql, "explanation": f"统计 {start} 至 {end} 的{caliber}"}
