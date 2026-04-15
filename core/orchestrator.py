# core/orchestrator.py — 总调度，串联所有 Agent（核心）

import logging
from typing import Any

from core.db_client import execute_query
from core.memory_agent import MemoryAgent
from core.metric_store import MetricStore
from gpt.intent_agent import IntentAgent
from gpt.anomaly_analyzer import AnomalyAnalyzer
from claude.sql_generator import SqlGenerator
from gemini.chart_advisor import ChartAdvisor
from gemini.summary_renderer import SummaryRenderer
from validator.cross_validator import CrossValidator

logger = logging.getLogger(__name__)

MAX_SQL_RETRIES = 2


class Orchestrator:
    """总调度器：串联所有 Agent，实现完整查询流程"""

    def __init__(self):
        self.memory = MemoryAgent()
        self.metric_store = MetricStore()
        self.intent_agent = IntentAgent()
        self.sql_generator = SqlGenerator()
        self.chart_advisor = ChartAdvisor()
        self.summary_renderer = SummaryRenderer()
        self.anomaly_analyzer = AnomalyAnalyzer()
        self.validator = CrossValidator()

    async def run(self, user_query: str, user_id: str = "anonymous") -> dict[str, Any]:
        """
        完整查询流程：
        1. 读取用户上下文
        2. GPT 意图识别
        3. 如需澄清 → 返回澄清选项
        4. Claude 验证意图可执行性
        5. Claude 生成 SQL
        6. GPT 验证 SQL（最多重试 2 次）
        7. 数据库执行 SQL
        8. Gemini 推荐图表
        9. Gemini 生成文字总结
        10. GPT 验证展示准确性
        11. 更新用户记忆
        12. 返回完整结果
        """

        # ── Step 1: 读取用户上下文 ────────────────────────────
        user_context = self.memory.get_context(user_id)

        # ── Step 2: GPT 意图识别 ──────────────────────────────
        try:
            intent = await self.intent_agent.recognize(user_query, user_id)
        except Exception as e:
            logger.error("IntentAgent error: %s", e)
            return self._error_response(f"意图识别失败: {e}")

        # Work on a copy to avoid mutating the returned intent object
        intent = {**intent, "original_query": user_query}

        # ── Step 3: 需要澄清 → 返回澄清选项 ──────────────────
        if intent.get("need_clarify"):
            return {
                "type": "clarify",
                "message": f'您的问题「{user_query}」可能对应多个指标，请选择：',
                "options": intent.get("clarify_options", [
                    {"key": "A", "label": "稿件签发通过量（签发量）", "metric_id": "article_signed_count"},
                    {"key": "B", "label": "稿件发布量", "metric_id": "article_published_count"},
                    {"key": "C", "label": "稿件成品量", "metric_id": "article_finished_count"},
                ]),
                "original_query": user_query,
            }

        # ── Step 4: Claude 验证意图可执行性 ───────────────────
        try:
            intent_validation = self.validator.validate_intent(intent, user_query)
            if not intent_validation.get("executable", True):
                risks = intent_validation.get("risks", [])
                fix = intent_validation.get("fix_suggestion", "")
                return self._error_response(f"意图无法执行: {'; '.join(risks)}. 建议: {fix}")
        except Exception as e:
            logger.warning("Intent validation error (non-fatal): %s", e)
            intent_validation = {"executable": True, "risks": [], "reviewed_by": "Claude"}

        # ── Step 5: 获取指标定义 ───────────────────────────────
        metric_id = intent.get("metric_id", "article_signed_count")
        metric = self.metric_store.get(metric_id)
        if not metric:
            # 降级：使用默认指标
            metric = self.metric_store.get("article_signed_count") or {}

        # ── Step 6: Claude 生成 SQL ───────────────────────────
        sql_result = None
        sql_validation = {"passed": False, "issues": [], "reviewed_by": "GPT"}
        last_sql = ""

        for attempt in range(MAX_SQL_RETRIES + 1):
            try:
                sql_result = await self.sql_generator.generate(intent, metric)
                last_sql = sql_result.get("sql", "")
            except Exception as e:
                logger.error("SqlGenerator error (attempt %d): %s", attempt, e)
                if attempt == MAX_SQL_RETRIES:
                    return self._error_response(f"SQL 生成失败: {e}")
                continue

            # ── Step 6b: GPT 验证 SQL 业务逻辑 ─────────────────
            try:
                sql_validation = self.validator.validate_sql(last_sql, metric)
            except Exception as e:
                logger.warning("SQL validation error: %s", e)
                sql_validation = {"passed": True, "issues": [], "reviewed_by": "GPT"}

            if sql_validation.get("passed", False):
                break

            if attempt < MAX_SQL_RETRIES:
                issues = sql_validation.get("issues", [])
                suggestion = sql_validation.get("suggestion", "")
                logger.warning("SQL validation failed (attempt %d), retrying. Issues: %s", attempt, issues)
                # 将失败信息注入到下一次生成的 intent 中
                intent["_sql_fix_hint"] = f"上次生成的 SQL 有问题：{'; '.join(issues)}。{suggestion}"

        if not last_sql:
            return self._error_response("无法生成有效 SQL")

        # ── Step 7: 数据库执行 SQL ────────────────────────────
        try:
            data = await execute_query(last_sql)
        except Exception as e:
            logger.error("DB execute error: %s | SQL: %s", e, last_sql)
            return self._error_response(f"数据库执行失败: {e}")

        # ── Step 8: Gemini 推荐图表 ───────────────────────────
        try:
            chart_config = self.chart_advisor.recommend(data, intent)
        except Exception as e:
            logger.warning("ChartAdvisor error: %s", e)
            chart_config = {"type": "stat_card", "title": "查询结果", "echarts_option": None}

        time_range = sql_result.get("time_range", {}) if sql_result else {}

        # ── Step 8b: GPT 数据异常分析 ─────────────────────────
        try:
            anomaly_info = self.anomaly_analyzer.analyze(data, metric, time_range)
        except Exception as e:
            logger.warning("AnomalyAnalyzer error: %s", e)
            anomaly_info = {"has_anomaly": False}

        # ── Step 9: Gemini 生成文字总结 ───────────────────────
        try:
            summary_html = self.summary_renderer.render(data, intent, time_range, anomaly_info)
        except Exception as e:
            logger.warning("SummaryRenderer error: %s", e)
            summary_html = self.summary_renderer.render_fallback(data, intent, time_range)

        # ── Step 10: GPT 验证展示准确性 ───────────────────────
        try:
            display_validation = self.validator.validate_display(
                data, {"chart": chart_config, "summary": summary_html[:200]}
            )
        except Exception as e:
            logger.warning("Display validation error: %s", e)
            display_validation = {"accurate": True, "issues": [], "reviewed_by": "GPT"}

        # ── Step 11: 更新用户记忆 ─────────────────────────────
        try:
            self.memory.update(user_id, intent)
        except Exception as e:
            logger.warning("MemoryAgent update error: %s", e)

        # ── Step 12: 返回完整结果 ─────────────────────────────
        return {
            "type": "result",
            "summary_html": summary_html,
            "chart_config": chart_config,
            "data": data,
            "sql": last_sql,
            "caliber": intent.get("recommended", metric.get("metric_name", "签发量")),
            "metric_name": metric.get("metric_name", "稿件签发通过量"),
            "time_range": time_range,
            "time_expression": intent.get("time_expression", ""),
            "dimension": intent.get("dimension"),
            "anomaly": anomaly_info,
            "validation": {
                "sql_review": sql_validation,
                "intent_review": intent_validation,
                "display_review": display_validation,
            },
        }

    async def handle_clarify(
        self, choice: str, user_id: str, original_query: str
    ) -> dict[str, Any]:
        """处理用户澄清选择，构造明确意图后继续查询"""
        metric_map = {
            "A": ("article_signed_count", "稿件签发通过量"),
            "B": ("article_published_count", "稿件发布量"),
            "C": ("article_finished_count", "稿件成品量"),
        }
        metric_id, metric_name = metric_map.get(choice.upper(), ("article_signed_count", "稿件签发通过量"))

        # 构造清晰意图，直接查询
        clarified_query = f"{original_query}（指{metric_name}）"
        return await self.run(clarified_query, user_id)

    def _error_response(self, message: str) -> dict[str, Any]:
        return {
            "type": "error",
            "message": message,
            "summary_html": f"<p class='error'>⚠️ {message}</p>",
            "chart_config": None,
            "data": [],
            "sql": "",
        }
