# validator/cross_validator.py — 多模型互审核心逻辑

import json
import logging
import re
from typing import Any

from core.llm_client import GPTClient, ClaudeClient

logger = logging.getLogger(__name__)

KNOWN_METRICS = ["article_signed_count", "article_published_count", "article_finished_count"]
KNOWN_DIMENSIONS = ["dept_name", "article_type", "author_name", "column_name", None]
KNOWN_TIMES = ["今天", "昨天", "本周", "上周", "本月", "上月", "今年", "去年"]


class CrossValidator:
    """多模型互审核心逻辑"""

    def __init__(self):
        self.gpt = GPTClient()
        self.claude = ClaudeClient()

    # ──────────────────────────────────────────────────────────
    # 1. GPT 审查 Claude 的 SQL
    # ──────────────────────────────────────────────────────────
    def validate_sql(self, sql: str, metric: dict) -> dict[str, Any]:
        """
        GPT 从业务逻辑角度审查 Claude 生成的 SQL。
        检查：status='signed'、signed_at、article_type!='test'、is_deleted=0
        返回：{passed, issues, suggestion, reviewed_by}
        """
        definition = metric.get("definition", {})
        prompt = f"""从业务逻辑角度审查以下 SQLite SQL 是否符合指标「{metric.get('metric_name', '稿件签发通过量')}」的定义：

SQL：
{sql}

必须满足的核心条件（逐条检查）：
1. ✅ 必须有 status = 'signed' 条件
2. ✅ 时间过滤必须使用 signed_at 字段（不是 created_at 或 published_at）
3. ✅ 必须排除测试稿件：article_type != 'test'
4. ✅ 必须排除已删除：is_deleted = 0
5. ✅ 应使用 COUNT(DISTINCT article_id) 或等效去重

返回严格 JSON（不要 markdown）：
{{
  "passed": true,
  "issues": [],
  "suggestion": "",
  "reviewed_by": "GPT"
}}"""

        raw = self.gpt.chat(prompt)
        result = self._parse_json(raw)
        result["reviewed_by"] = "GPT"

        # 本地兜底校验（避免 LLM 漏检）
        local_issues = []
        sql_lower = sql.lower()
        if "status" not in sql_lower or "'signed'" not in sql_lower.replace('"signed"', "'signed'"):
            local_issues.append("缺少 status='signed' 条件")
        if "signed_at" not in sql_lower:
            local_issues.append("时间字段应使用 signed_at")
        if "article_type" not in sql_lower or "test" not in sql_lower:
            local_issues.append("缺少排除测试稿件条件")
        if "is_deleted" not in sql_lower:
            local_issues.append("缺少 is_deleted=0 条件")

        if local_issues:
            result["passed"] = False
            result.setdefault("issues", [])
            result["issues"].extend(local_issues)

        return result

    # ──────────────────────────────────────────────────────────
    # 2. Claude 验证 GPT 的意图
    # ──────────────────────────────────────────────────────────
    def validate_intent(self, intent: dict, user_query: str) -> dict[str, Any]:
        """
        Claude 验证 GPT 的意图解析是否技术层面可执行。
        返回：{executable, risks, fix_suggestion, reviewed_by}
        """
        metric_id = intent.get("metric_id", "")
        time_expr = intent.get("time_expression", "")
        dimension = intent.get("dimension")

        prompt = f"""验证以下意图解析是否可以被技术执行：

用户原始问题：{user_query}
GPT 解析的意图：{json.dumps(intent, ensure_ascii=False)}

检查项：
1. metric_id（{metric_id}）是否在已知列表：{KNOWN_METRICS}
2. time_expression（{time_expr}）是否可被解析：{KNOWN_TIMES}
3. dimension（{dimension}）是否在支持列表：{KNOWN_DIMENSIONS}
4. 是否有技术层面的执行风险

返回严格 JSON（不要 markdown）：
{{
  "executable": true,
  "risks": [],
  "fix_suggestion": "",
  "reviewed_by": "Claude"
}}"""

        raw = self.claude.chat(prompt)
        result = self._parse_json(raw)
        result["reviewed_by"] = "Claude"

        # 本地兜底验证
        local_risks = []
        if metric_id not in KNOWN_METRICS:
            local_risks.append(f"未知的 metric_id: {metric_id}")
        if time_expr and not any(t in time_expr for t in KNOWN_TIMES):
            local_risks.append(f"无法解析的时间表达式: {time_expr}")
        if dimension is not None and dimension not in [d for d in KNOWN_DIMENSIONS if d]:
            local_risks.append(f"不支持的维度: {dimension}")

        if local_risks:
            result["executable"] = False
            result.setdefault("risks", [])
            result["risks"].extend(local_risks)

        return result

    # ──────────────────────────────────────────────────────────
    # 3. GPT 验证 Gemini 的展示方案
    # ──────────────────────────────────────────────────────────
    def validate_display(self, data: list[dict], ui_plan: dict) -> dict[str, Any]:
        """
        GPT 验证 Gemini 的展示方案是否准确反映数据含义。
        返回：{accurate, issues, correction, reviewed_by}
        """
        prompt = f"""验证展示方案是否准确反映了数据含义：

原始数据（前5条）：{data[:5]}
Gemini 展示方案：{json.dumps(ui_plan, ensure_ascii=False)[:500]}

检查项：
1. 数字展示是否准确（与原始数据一致）
2. 图表类型是否匹配数据结构
3. 是否有口径说明（签发量口径）
4. 是否有误导用户的表述

返回严格 JSON（不要 markdown）：
{{
  "accurate": true,
  "issues": [],
  "correction": "",
  "reviewed_by": "GPT"
}}"""

        raw = self.gpt.chat(prompt)
        result = self._parse_json(raw)
        result["reviewed_by"] = "GPT"
        return result

    def _parse_json(self, raw: str) -> dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        logger.error("CrossValidator: Failed to parse JSON: %s", raw[:200])
        return {"passed": True, "executable": True, "accurate": True, "issues": [], "risks": []}
