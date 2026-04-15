"""
核心编排器（Orchestrator）
协调多个 Agent 完成端到端的稿件指标查询
"""

import aiosqlite
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import config
from gpt.intent_agent import IntentAgent
from gpt.logic_validator import LogicValidator
from claude.sql_generator import SQLGenerator
from claude.code_reviewer import CodeReviewer
from gemini.summary_renderer import SummaryRenderer
from gemini.chart_advisor import ChartAdvisor
from validator.cross_validator import CrossValidator


def _resolve_time_range(time_range: dict) -> dict:
    """将相对时间描述解析为具体日期范围"""
    today = date.today()
    tr_type = time_range.get("type", "year")

    if tr_type == "year":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
    elif tr_type == "month":
        start = date(today.year, today.month, 1)
        end = (start + relativedelta(months=1)) - relativedelta(days=1)
    elif tr_type == "week":
        start = today - relativedelta(days=today.weekday())
        end = start + relativedelta(days=6)
    elif tr_type == "day":
        start = end = today
    else:
        # custom or already set
        start = time_range.get("start") or date(today.year, 1, 1)
        end = time_range.get("end") or today

    return {
        "type": tr_type,
        "start": str(start) if not isinstance(start, str) else start,
        "end": str(end) if not isinstance(end, str) else end,
    }


class Orchestrator:
    """多模型协作编排器"""

    def __init__(self):
        self.intent_agent = IntentAgent()
        self.sql_generator = SQLGenerator()
        self.code_reviewer = CodeReviewer()
        self.summary_renderer = SummaryRenderer()
        self.chart_advisor = ChartAdvisor()
        self.logic_validator = LogicValidator()
        self.cross_validator = CrossValidator()

    async def run(self, user_query: str, user_id: str = "anonymous") -> dict:
        """
        端到端处理流程：
        1. GPT 解析意图
        2. Claude 验证意图
        3. Claude 生成 SQL
        4. Claude 代码审查
        5. GPT 交叉验证 SQL
        6. 执行查询
        7. GPT 逻辑校验结果
        8. Gemini 渲染总结
        9. Gemini 推荐图表
        10. GPT 验证展示内容
        """
        # Step 1: 意图解析
        intent = await self.intent_agent.parse(user_query)

        # 解析时间范围
        if "time_range" in intent:
            intent["time_range"] = _resolve_time_range(intent["time_range"])

        # Step 2: 如果存在歧义，请求用户澄清
        if intent.get("ambiguous"):
            return {
                "type": "clarify",
                "options": intent.get("ambiguous_options", []),
                "message": "您的查询存在歧义，请选择统计口径",
            }

        # Step 3: Claude 生成 SQL
        sql_result = await self.sql_generator.generate(intent)
        sql = sql_result.get("sql", "")

        # Step 4: 代码审查（安全检查）
        review = await self.code_reviewer.review(sql)
        if not review.get("safe", True):
            return {
                "type": "error",
                "message": f"SQL 安全检查未通过：{'; '.join(review.get('issues', []))}",
            }
        sql = review.get("approved_sql", sql)

        # Step 5: 交叉验证 SQL（GPT 验证 Claude 生成的 SQL）
        sql_validation = await self.cross_validator.validate_sql(sql, intent)
        sql = sql_validation.get("fixed_sql", sql)

        # Step 6: 执行查询
        query_result = await self._execute_query(sql)

        # Step 7: 逻辑校验
        logic_check = await self.logic_validator.validate(query_result, intent)
        if not logic_check.get("valid", True):
            issues = logic_check.get("issues", [])
            # 记录警告但不阻断流程
            query_result["_warnings"] = issues

        # Step 8: Gemini 渲染总结
        summary = await self.summary_renderer.render(query_result, intent)

        # Step 9: Gemini 推荐图表
        chart = await self.chart_advisor.advise(query_result, intent)

        # Step 10: GPT 验证展示内容
        display_check = await self.cross_validator.validate_display(
            summary.get("summary_html", ""), query_result
        )

        return {
            "type": "result",
            "summary_html": summary.get("summary_html", ""),
            "key_metrics": summary.get("key_metrics", []),
            "insight": summary.get("insight", ""),
            "chart": chart,
            "sql": sql,
            "caliber": intent.get("caliber", "签发量"),
            "time_range": intent.get("time_range", {}),
            "raw_data": query_result,
            "display_valid": display_check.get("valid", True),
        }

    async def _execute_query(self, sql: str) -> dict:
        """执行 SQL 查询并返回结果"""
        try:
            async with aiosqlite.connect(config.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(sql) as cursor:
                    rows = await cursor.fetchall()
                    if not rows:
                        return {"total": 0, "rows": []}
                    # 转换为字典列表
                    row_dicts = [dict(row) for row in rows]
                    # 如果只有一行且包含 total/count，提取为顶层字段
                    if len(row_dicts) == 1:
                        result = dict(row_dicts[0])
                        result["rows"] = row_dicts
                        return result
                    return {"total": len(row_dicts), "rows": row_dicts}
        except Exception as e:
            return {"total": 0, "rows": [], "error": str(e)}
