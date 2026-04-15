# claude/sql_generator.py — SQL 生成（Claude）

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from core.llm_client import ClaudeClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的 SQL 工程师，专注于新闻媒体数据仓库查询。
你的任务是根据指标定义和用户意图生成精准的 SQLite SQL。
只返回 SQL 语句本身，不要有 markdown 代码块，不要有解释。"""


class SqlGenerator:
    """SQL 生成（Claude 负责）"""

    def __init__(self):
        self.claude = ClaudeClient()

    def _parse_time(self, expression: str) -> tuple[str, str]:
        """时间表达式 → (start_date, end_date) ISO 格式"""
        now = datetime.now()
        today = now.date()

        mapping = {
            "今天": (today, today),
            "昨天": (today - timedelta(days=1), today - timedelta(days=1)),
            "本周": (today - timedelta(days=today.weekday()), today),
            "上周": (
                today - timedelta(days=today.weekday() + 7),
                today - timedelta(days=today.weekday() + 1),
            ),
            "本月": (today.replace(day=1), today),
            "上月": (
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                today.replace(day=1) - timedelta(days=1),
            ),
            "今年": (today.replace(month=1, day=1), today),
            "去年": (
                today.replace(year=today.year - 1, month=1, day=1),
                today.replace(year=today.year - 1, month=12, day=31),
            ),
        }

        for key, (start, end) in mapping.items():
            if key in expression:
                return str(start), str(end)

        # 默认今年
        return str(today.replace(month=1, day=1)), str(today)

    def _parse_dimension(self, dimension: Optional[str], metric: dict) -> str:
        """维度名 → GROUP BY SQL 片段"""
        if not dimension:
            return ""
        dim_map = {
            "dept_name": "GROUP BY a.dept_name ORDER BY signed_count DESC",
            "article_type": "GROUP BY a.article_type ORDER BY signed_count DESC",
            "author_name": "GROUP BY a.author_name ORDER BY signed_count DESC",
            "column_name": "GROUP BY a.column_name ORDER BY signed_count DESC",
        }
        return dim_map.get(dimension, f"GROUP BY a.{dimension}")

    async def generate(self, intent: dict, metric: dict) -> dict[str, Any]:
        """
        基于意图和指标定义生成 SQL。
        返回 {metric, sql, time_range, dimension}
        """
        time_expr = intent.get("time_expression", "今年")
        dimension = intent.get("dimension")

        start_date, end_date = self._parse_time(time_expr)
        group_by_sql = self._parse_dimension(dimension, metric)

        # 获取 sql_template
        sql_template = metric.get("data_source", {}).get("sql_template", "")

        if sql_template:
            # 处理模板中的 dimension_filter
            if dimension and group_by_sql:
                # 需要在 SELECT 中加入维度字段
                dim_select = f"a.{dimension},"
                dim_filter = group_by_sql
            else:
                dim_select = ""
                dim_filter = ""

            prompt = f"""根据以下指标定义的 SQL 模板，生成一个完整可执行的 SQLite 查询：

指标名称：{metric.get('metric_name', '')}
SQL 模板：
{sql_template}

查询参数：
- start_date: {start_date}
- end_date: {end_date} 23:59:59
- dimension: {dimension or '无'}
- dimension_filter: {dim_filter}

要求：
1. 如果有维度（{dimension}），在 SELECT 中加入该字段，并在末尾加上 {group_by_sql or 'GROUP BY 对应字段'}
2. 使用 COUNT(DISTINCT a.article_id) AS signed_count
3. status = 'signed'，时间用 signed_at，排除 article_type='test'，is_deleted=0
4. 只返回 SQL，不要 markdown，不要解释

生成的 SQL："""
        else:
            prompt = f"""生成 SQLite SQL 查询：

表：fact_article_workflow（别名 a）
条件：status = 'signed'，signed_at BETWEEN '{start_date}' AND '{end_date} 23:59:59'
      article_type != 'test'，is_deleted = 0
统计：COUNT(DISTINCT a.article_id) AS signed_count
维度：{dimension or '无'}
{f'GROUP BY a.{dimension} ORDER BY signed_count DESC' if dimension else ''}

只返回 SQL，不要 markdown："""

        raw_sql = self.claude.chat(prompt, system=SYSTEM_PROMPT)
        sql = self._clean_sql(raw_sql)

        return {
            "metric": metric.get("metric_id", "article_signed_count"),
            "sql": sql,
            "time_range": {"start": start_date, "end": end_date},
            "dimension": dimension,
        }

    def _clean_sql(self, raw: str) -> str:
        """清洗 SQL：去掉 markdown 代码块"""
        sql = re.sub(r"```(?:sql)?", "", raw).strip().strip("`").strip()
        # 去掉前导说明文字（保留第一个 SELECT 开始的部分）
        match = re.search(r"(?i)(SELECT\s.+)", sql, re.DOTALL)
        if match:
            sql = match.group(1).strip()
        return sql
