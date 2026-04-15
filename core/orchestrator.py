# core/orchestrator.py
# 职责：总调度，串联所有 Agent，实现完整异步查询流水线
# 模型：全部三个（GPT / Claude / Gemini）

import logging

from core.db_client import execute_query
from core.memory_agent import MemoryAgent
from core.metric_store import MetricStore
from gemini.chart_advisor import ChartAdvisor
from gemini.summary_renderer import SummaryRenderer
from gemini.ui_designer import UIDesigner
from gpt.anomaly_analyzer import AnomalyAnalyzer
from gpt.intent_agent import IntentAgent
from gpt.logic_validator import LogicValidator
from claude.code_reviewer import CodeReviewer
from claude.sql_generator import SQLGenerator
from validator.cross_validator import CrossValidator

logger = logging.getLogger(__name__)


class Orchestrator:
    """主调度器，异步串联全流水线"""

    def __init__(self):
        self.memory = MemoryAgent()
        self.intent_agent = IntentAgent()
        self.code_reviewer = CodeReviewer()
        self.sql_generator = SQLGenerator()
        self.logic_validator = LogicValidator()
        self.anomaly_analyzer = AnomalyAnalyzer()
        self.chart_advisor = ChartAdvisor()
        self.summary_renderer = SummaryRenderer()
        self.ui_designer = UIDesigner()
        self.cross_validator = CrossValidator()
        self.metric_store = MetricStore()

    async def run(self, user_query: str, user_id: str) -> dict:
        """
        完整异步调度流程：
        1  memory.get_context
        2  intent_agent (GPT)
        3  if need_clarify → return clarify
        4  code_reviewer (Claude) 验证意图可执行
        5  sql_generator (Claude) 生成 SQL
        6  logic_validator (GPT) 验证 SQL
        7  if not passed → retry sql_generator once
        8  db_client.execute_query
        9  anomaly_analyzer (GPT)
        10 chart_advisor (Gemini)
        11 summary_renderer (Gemini)
        12 validate_display (GPT via CrossValidator)
        13 memory.update
        14 return final result
        """
        # ── 1. 用户上下文 ─────────────────────────────────────
        user_context = self.memory.get_context(user_id)

        # ── 2. 意图识别（GPT）────────────────────────────────
        try:
            intent = self.intent_agent.run(user_query, user_context)
        except Exception as e:
            logger.error("IntentAgent failed: %s", e)
            return {"type": "error", "message": f"意图识别失败：{e}"}

        # 方便后续模块使用原始问题
        intent["_original_query"] = user_query

        # ── 3. 需要澄清 ────────────────────────────────────────
        if intent.get("need_clarify"):
            clarify_html = self.ui_designer.run(intent)
            return {
                "type": "clarify",
                "html": clarify_html,
                "intent": intent,
                "message": f"您的问题涉及多个统计口径，请选择您要查询的指标。",
            }

        # ── 4. 审查意图可执行性（Claude）────────────────────────
        try:
            review = self.code_reviewer.run(intent)
            if not review.get("executable", True):
                return {
                    "type": "error",
                    "message": f"意图不可执行：{'; '.join(review.get('risks', []))}",
                    "fix_suggestion": review.get("fix_suggestion", ""),
                }
        except Exception as e:
            logger.warning("CodeReviewer failed (non-critical): %s", e)

        # ── 5. SQL 生成（Claude）──────────────────────────────
        try:
            sql_result = self.sql_generator.run(intent, user_query)
        except Exception as e:
            logger.error("SQLGenerator failed: %s", e)
            return {"type": "error", "message": f"SQL 生成失败：{e}"}

        sql = sql_result.get("sql", "")
        time_range = sql_result.get("time_range", {})

        # ── 6. 业务规则校验（GPT）────────────────────────────
        metric = self.metric_store.get(intent.get("metric_id", ""))
        try:
            validation = self.logic_validator.run(sql, metric or {})
        except Exception as e:
            logger.warning("LogicValidator failed (non-critical): %s", e)
            validation = {"passed": True}

        # ── 7. 校验失败 → 重试一次 ────────────────────────────
        if not validation.get("passed", True):
            logger.warning("SQL validation failed, retrying... issues=%s", validation.get("issues"))
            try:
                sql_result = self.sql_generator.run(intent, user_query)
                sql = sql_result.get("sql", "")
            except Exception as e:
                logger.error("SQLGenerator retry failed: %s", e)

        # ── 8. 执行查询 ────────────────────────────────────────
        query_result = await execute_query(sql)
        if query_result.get("error"):
            return {
                "type": "error",
                "message": f"数据库查询失败：{query_result['error']}",
                "sql": sql,
            }

        data = query_result.get("data", [])

        # ── 9. 异常检测（GPT）────────────────────────────────
        anomaly = {"is_anomaly": False, "reason": "", "suggestion": ""}
        if metric:
            try:
                anomaly = self.anomaly_analyzer.run(data, metric)
            except Exception as e:
                logger.warning("AnomalyAnalyzer failed (non-critical): %s", e)

        # ── 10. 图表推荐（Gemini）────────────────────────────
        try:
            chart = self.chart_advisor.run(data, intent.get("dimension"))
        except Exception as e:
            logger.warning("ChartAdvisor failed (non-critical): %s", e)
            chart = {"chart_type": "card", "echarts_option": {}, "card_value": 0}

        # ── 11. 文字总结（Gemini）────────────────────────────
        try:
            summary_html = self.summary_renderer.run(data, metric or {}, time_range, anomaly)
        except Exception as e:
            logger.warning("SummaryRenderer failed (non-critical): %s", e)
            summary_html = "<p>数据查询完成。</p>"

        # ── 12. 展示方案验证（GPT via CrossValidator）──────────
        try:
            self.cross_validator.validate_display(data, chart)
        except Exception as e:
            logger.warning("CrossValidator.validate_display failed (non-critical): %s", e)

        # ── 13. 更新记忆 ────────────────────────────────────────
        try:
            self.memory.update(user_id, intent)
        except Exception as e:
            logger.warning("MemoryAgent.update failed (non-critical): %s", e)

        # ── 14. 返回最终结果 ──────────────────────────────────
        return {
            "type": "result",
            "summary_html": summary_html,
            "data": data,
            "sql": sql,
            "chart": chart,
            "anomaly": anomaly,
            "caliber": intent.get("metric_name", "稿件签发通过量"),
            "time_range": time_range,
            "metric_id": intent.get("metric_id", ""),
            "dimension": intent.get("dimension"),
            "validation": validation,
        }

    async def run_clarify(
        self,
        choice: str,
        user_id: str,
        original_query: str,
    ) -> dict:
        """处理用户澄清选项，继续查询流程"""
        from gemini.ui_designer import CALIBER_OPTIONS

        selected = next(
            (o for o in CALIBER_OPTIONS if o["label"] == choice.upper()),
            CALIBER_OPTIONS[0],
        )

        # 构造确定的意图，跳过再次澄清
        intent = {
            "metric_id": selected["metric_id"],
            "metric_name": selected["name"],
            "ambiguous": False,
            "ambiguous_reason": "",
            "recommended": selected["name"],
            "time_expression": "今年",
            "dimension": None,
            "confidence": 0.99,
            "need_clarify": False,
            "_original_query": original_query,
        }

        # 更新用户偏好
        self.memory.update(user_id, intent)

        # 从 SQL 生成步骤继续
        try:
            sql_result = self.sql_generator.run(intent, original_query)
        except Exception as e:
            return {"type": "error", "message": f"SQL 生成失败：{e}"}

        sql = sql_result.get("sql", "")
        time_range = sql_result.get("time_range", {})

        query_result = await execute_query(sql)
        if query_result.get("error"):
            return {"type": "error", "message": f"查询失败：{query_result['error']}", "sql": sql}

        data = query_result.get("data", [])
        metric = self.metric_store.get(selected["metric_id"]) or {}

        chart = self.chart_advisor.run(data)
        summary_html = self.summary_renderer.run(data, metric, time_range)

        return {
            "type": "result",
            "summary_html": summary_html,
            "data": data,
            "sql": sql,
            "chart": chart,
            "anomaly": {"is_anomaly": False, "reason": "", "suggestion": ""},
            "caliber": selected["name"],
            "time_range": time_range,
            "metric_id": selected["metric_id"],
            "dimension": None,
        }
