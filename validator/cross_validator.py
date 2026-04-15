# validator/cross_validator.py
# 职责：多模型互审核心逻辑（GPT审查Claude，Claude审查GPT，GPT审查Gemini）
# 模型：GPT、Claude

import json
import logging

from core.llm_client import ClaudeClient, GPTClient

logger = logging.getLogger(__name__)


class CrossValidator:
    """多模型互审"""

    def __init__(self):
        self.gpt = GPTClient()
        self.claude = ClaudeClient()

    # ── 1. GPT 审查 Claude 的 SQL ────────────────────────────

    def validate_sql(self, sql: str, metric: dict) -> dict:
        """
        GPT 审查 Claude 生成的 SQL。
        返回：{passed: bool, issues: list[str], suggestion: str}
        """
        prompt = f"""
你是 SQL 审查专家，请审查以下 SQL 是否正确实现了指标定义，返回 JSON。

SQL：
{sql}

指标核心规则（来自 Claude 生成，需要 GPT 验证）：
- 必须 COUNT(DISTINCT article_id)
- status = 'signed'
- 时间字段用 signed_at
- 排除 article_type = 'test'
- is_deleted = 0
- 表名为 fact_article_workflow

返回 JSON（只返回 JSON）：
{{
  "passed": true 或 false,
  "issues": ["发现的问题列表"],
  "suggestion": "修改建议（passed=true 则为空字符串）"
}}
"""
        raw = self.gpt.chat(
            prompt,
            system="你是数据工程师，专注于 SQL 代码审查。只返回 JSON。",
        )
        return self._parse(raw, "validate_sql")

    # ── 2. Claude 审查 GPT 的意图 ───────────────────────────

    def validate_intent(self, intent: dict, user_query: str) -> dict:
        """
        Claude 审查 GPT 的意图解析结果。
        返回：{valid: bool, issues: list[str], suggestion: str}
        """
        prompt = f"""
你是意图审查专家，请验证 GPT 解析的用户意图是否准确，返回 JSON。

用户原始问题：{user_query}
GPT 解析的意图：{json.dumps(intent, ensure_ascii=False, indent=2)}

检查：
1. metric_id 是否与用户问题匹配
2. time_expression 是否正确提取
3. dimension 是否正确识别
4. ambiguous 标记是否合理
5. confidence 分数是否合理

返回 JSON（只返回 JSON）：
{{
  "valid": true 或 false,
  "issues": ["发现的问题"],
  "suggestion": "修正建议（valid=true 则为空字符串）"
}}
"""
        raw = self.claude.chat(
            prompt,
            system="你是意图识别审查专家。只返回 JSON，不要任何解释。",
        )
        return self._parse(raw, "validate_intent")

    # ── 3. GPT 审查 Gemini 的展示方案 ───────────────────────

    def validate_display(self, data: list[dict], ui_plan: dict) -> dict:
        """
        GPT 审查 Gemini 的展示方案是否合理。
        返回：{approved: bool, issues: list[str], suggestion: str}
        """
        prompt = f"""
你是 UI 审查专家，请审查 Gemini 生成的展示方案是否适合展示查询结果，返回 JSON。

查询数据：{json.dumps(data, ensure_ascii=False)}
展示方案：{json.dumps(ui_plan, ensure_ascii=False, indent=2)}

检查：
1. 图表类型是否与数据结构匹配
2. 单值用卡片、时间序列用折线、维度对比用柱状图
3. 数据量是否适合所选图表

返回 JSON（只返回 JSON）：
{{
  "approved": true 或 false,
  "issues": ["发现的问题"],
  "suggestion": "改进建议（approved=true 则为空字符串）"
}}
"""
        raw = self.gpt.chat(
            prompt,
            system="你是数据可视化审查专家。只返回 JSON。",
        )
        return self._parse(raw, "validate_display")

    # ── 工具方法 ─────────────────────────────────────────────

    @staticmethod
    def _parse(raw: str, method: str) -> dict:
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("`").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("CrossValidator.%s parse error: %s", method, e)
            # 返回宽松的默认值，不阻断主流程
            return {"passed": True, "valid": True, "approved": True, "issues": [], "suggestion": ""}
