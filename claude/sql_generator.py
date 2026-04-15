# claude/sql_generator.py
# 职责：根据意图和指标定义生成 SQL
# 模型：Claude claude-3-5-sonnet

import logging
import re
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from core.llm_client import ClaudeClient
from core.metric_store import MetricStore

logger = logging.getLogger(__name__)

_SYSTEM = """你是专业的 SQL 工程师，专注于数据指标查询。
严格按照给定的 SQL 模板生成 SQL，只输出最终 SQL 代码，不要任何解释、注释或 markdown 代码块。"""


class SQLGenerator:
    """SQL 生成（Claude）"""

    def __init__(self):
        self.llm = ClaudeClient()
        self.metric_store = MetricStore()

    def run(self, intent: dict, user_query: str) -> dict:
        """
        返回：{sql: str, time_range: dict, dimension: str|None}
        """
        metric = self.metric_store.get(intent.get("metric_id", "article_signed_count"))
        if not metric:
            return {"sql": "", "time_range": {}, "dimension": None, "error": "指标不存在"}

        time_range = self._parse_time(intent.get("time_expression", "今年"))
        dimension_sql = self._parse_dimension(intent.get("dimension"), metric)

        template = metric.get("data_source", {}).get("sql_template", "")

        prompt = f"""
根据以下指标定义生成精确的 SQL 查询语句。

【指标名称】{metric.get('metric_name')}

【SQL 模板】
{template}

【参数】
- 开始时间：{time_range['start']}
- 结束时间：{time_range['end']}
- 维度过滤（替换 {{dimension_filter}}）：{dimension_sql if dimension_sql else '（空，无需添加）'}

【规则】
1. 严格使用模板中的表名 fact_article_workflow 和字段名
2. status = 'signed' 条件必须保留
3. 时间字段使用 signed_at
4. 必须包含 is_deleted = 0 和排除 article_type = 'test'
5. 如果有维度，在 SELECT 中添加维度字段，并加 GROUP BY
6. 只输出 SQL，不要解释

用户原始问题：{user_query}
"""
        raw_sql = self.llm.chat(prompt, system=_SYSTEM)
        sql = self._clean_sql(raw_sql)

        # 如果 Claude 返回异常，回退到模板填充
        if not sql or sql.startswith("[Claude Error]"):
            sql = self._fallback_sql(template, time_range, dimension_sql)

        return {
            "sql": sql,
            "time_range": time_range,
            "dimension": intent.get("dimension"),
        }

    # ── 时间解析 ──────────────────────────────────────────────

    @staticmethod
    def _parse_time(expression: str) -> dict:
        """自然语言时间 → {start: 'YYYY-MM-DD', end: 'YYYY-MM-DD'}"""
        today = date.today()

        mapping: dict[str, dict] = {
            "今天": {
                "start": str(today),
                "end": str(today),
            },
            "昨天": {
                "start": str(today - timedelta(days=1)),
                "end": str(today - timedelta(days=1)),
            },
            "本周": {
                "start": str(today - timedelta(days=today.weekday())),
                "end": str(today),
            },
            "上周": {
                "start": str(today - timedelta(days=today.weekday() + 7)),
                "end": str(today - timedelta(days=today.weekday() + 1)),
            },
            "本月": {
                "start": str(today.replace(day=1)),
                "end": str(today),
            },
            "上月": {
                "start": str((today - relativedelta(months=1)).replace(day=1)),
                "end": str((today.replace(day=1)) - timedelta(days=1)),
            },
            "今年": {
                "start": str(today.replace(month=1, day=1)),
                "end": str(today),
            },
            "去年": {
                "start": str(today.replace(year=today.year - 1, month=1, day=1)),
                "end": str(today.replace(year=today.year - 1, month=12, day=31)),
            },
        }
        # 别名兼容
        alias = {
            "上个月": "上月",
            "这个月": "本月",
            "这周": "本周",
            "今日": "今天",
            "明天": "今天",
        }
        expr = alias.get(expression, expression)
        return mapping.get(expr, mapping["今年"])

    # ── 维度解析 ──────────────────────────────────────────────

    @staticmethod
    def _parse_dimension(dimension: str | None, metric: dict) -> str:
        """维度名 → SQL GROUP BY 片段"""
        if not dimension:
            return ""
        dims = {d["name"]: d["field"] for d in metric.get("dimensions", [])}
        # 也支持直接传字段名
        for d in metric.get("dimensions", []):
            for alias in d.get("alias", []):
                dims[alias] = d["field"]

        field = dims.get(dimension)
        if field:
            return f", {field} GROUP BY {field}"
        return ""

    # ── SQL 清洗 ──────────────────────────────────────────────

    @staticmethod
    def _clean_sql(raw: str) -> str:
        sql = raw.strip()
        # 去掉 markdown 代码块
        sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\s*```$", "", sql)
        return sql.strip()

    # ── 降级 SQL ──────────────────────────────────────────────

    @staticmethod
    def _fallback_sql(template: str, time_range: dict, dimension_sql: str) -> str:
        sql = template.replace("{start_date}", time_range.get("start", ""))
        sql = sql.replace("{end_date}", time_range.get("end", ""))
        sql = sql.replace("{dimension_filter}", dimension_sql)
        return sql.strip()
