# claude/code_reviewer.py
# 职责：审查意图是否可技术执行
# 模型：Claude claude-3-5-sonnet

import json
import logging

from core.llm_client import ClaudeClient
from core.metric_store import MetricStore

logger = logging.getLogger(__name__)

_SYSTEM = """你是数据查询意图审查专家，负责评估用户意图是否可以被技术执行。
只返回 JSON，不要任何额外内容。"""


class CodeReviewer:
    """意图可执行性审查（Claude）"""

    def __init__(self):
        self.llm = ClaudeClient()
        self.metric_store = MetricStore()

    def run(self, intent: dict) -> dict:
        """
        审查意图是否可技术执行。
        返回：{executable: bool, risks: list[str], fix_suggestion: str}
        """
        # 本地快速检查
        local_risks = self._local_check(intent)

        prompt = f"""
请审查以下用户查询意图是否可以被技术执行：

意图：{json.dumps(intent, ensure_ascii=False, indent=2)}

可用指标 ID 列表：{[m.get('metric_id') for m in self.metric_store.all()]}

检查以下项目：
1. metric_id 是否在可用指标列表中
2. time_expression 是否是支持的时间表达式（今天/昨天/本周/上周/本月/上月/今年/去年）
3. dimension 是否在支持的维度列表中（部门/稿件类型/作者/栏目 或 null）
4. 意图整体是否逻辑合理

本地检查发现的问题：{local_risks}

返回 JSON：
{{
  "executable": true 或 false,
  "risks": ["风险1", "风险2"],
  "fix_suggestion": "修复建议（可执行则为空字符串）"
}}
"""
        raw = self.llm.chat(prompt, system=_SYSTEM)
        result = self._parse_json(raw)

        # 合并本地检查
        if local_risks:
            result.setdefault("risks", [])
            for r in local_risks:
                if r not in result["risks"]:
                    result["risks"].append(r)
            if result["risks"]:
                result["executable"] = False

        return result

    # ── 本地检查 ──────────────────────────────────────────────

    def _local_check(self, intent: dict) -> list[str]:
        risks = []
        metric_id = intent.get("metric_id", "")
        if metric_id and not self.metric_store.get(metric_id):
            risks.append(f"指标 {metric_id} 不存在于指标字典中")

        time_expr = intent.get("time_expression", "")
        supported_times = {
            "今天", "昨天", "本周", "上周", "本月", "上月", "今年", "去年",
            "上个月", "这个月", "这周", "今日",
        }
        if time_expr and time_expr not in supported_times:
            risks.append(f"时间表达式 '{time_expr}' 不在支持范围内")

        return risks

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("`").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("CodeReviewer JSON parse error: %s", e)
            return {"executable": True, "risks": [], "fix_suggestion": ""}
