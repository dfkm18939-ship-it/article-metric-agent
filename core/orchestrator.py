"""
core/orchestrator.py
协调器 — 串联所有 Agent，完成完整的查询流程
"""

from gpt.intent_agent import IntentAgent
from gpt.logic_validator import LogicValidator
from gpt.anomaly_analyzer import AnomalyAnalyzer
from claude.sql_generator import SQLGenerator
from claude.code_reviewer import CodeReviewer
from gemini.summary_renderer import SummaryRenderer
from core.metric_store import metric_store


class Orchestrator:
    """
    查询流程协调器
    流程：意图识别 → 业务校验 → SQL生成 → SQL审查 → 执行 → 异常分析 → 结果总结
    """

    def __init__(self):
        self.intent_agent = IntentAgent()
        self.validator = LogicValidator()
        self.sql_generator = SQLGenerator()
        self.code_reviewer = CodeReviewer()
        self.anomaly_analyzer = AnomalyAnalyzer()
        self.summary_renderer = SummaryRenderer()

    async def run(self, user_query: str, user_id: str = "default") -> dict:
        """
        执行完整查询流程

        Args:
            user_query: 用户原始查询文本
            user_id: 用户标识

        Returns:
            dict: 包含 type（result/clarify/error）和相关数据的响应字典
        """
        try:
            # 1. 意图识别
            intent = await self.intent_agent.recognize(user_query)

            # 2. 业务逻辑校验
            validation = await self.validator.validate(intent)

            # 3. 指标检索（RAG）
            matched_metrics = await metric_store.search(user_query, top_k=1)
            caliber = matched_metrics[0]["name"] if matched_metrics else "签发量"

            # 4. SQL 生成
            sql = await self.sql_generator.generate(intent)

            # 5. SQL 安全审查
            review = await self.code_reviewer.review_sql(sql)

            # 6. 模拟数据（真实场景替换为数据库查询；0 为占位值）
            mock_data = [{"metric_type": caliber, "count": 0}]

            # 7. 异常分析
            anomaly = await self.anomaly_analyzer.analyze(mock_data, {"caliber": caliber})

            # 8. 结果总结
            summary = await self.summary_renderer.render(
                mock_data, {"caliber": caliber, "query": user_query}
            )

            return {
                "type": "result",
                "caliber": caliber,
                "sql": sql,
                "data": mock_data,
                "summary": summary,
                "anomaly": anomaly,
                "time_range": {"start": "", "end": ""},
            }

        except Exception as e:
            return {"type": "error", "message": str(e)}
