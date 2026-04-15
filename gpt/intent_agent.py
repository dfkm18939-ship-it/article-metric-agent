# gpt/intent_agent.py
# 职责：意图识别 + 歧义判断
# 模型：GPT-4o

import json
import logging

from core.llm_client import GPTClient
from core.metric_store import MetricStore

logger = logging.getLogger(__name__)

_SYSTEM = """你是数据指标意图识别专家，专注于新闻媒体生产系统的稿件指标查询。
请严格按照指定 JSON 格式返回结果，不要输出任何额外内容。"""


class IntentAgent:
    """意图识别 + 歧义判断（GPT）"""

    def __init__(self):
        self.llm = GPTClient()
        self.metric_store = MetricStore()

    def run(self, user_query: str, user_context: dict) -> dict:
        candidates = self.metric_store.search(user_query, k=3)
        preference = user_context.get("preference", {})
        role = user_context.get("role", "editor")

        prompt = f"""
用户问题：{user_query}
用户角色：{role}
用户历史偏好：{json.dumps(preference, ensure_ascii=False)}

候选指标列表：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

请分析用户意图，返回以下 JSON（只返回 JSON，不要 markdown 代码块）：
{{
  "metric_id": "匹配的指标ID，如 article_signed_count",
  "metric_name": "指标中文名",
  "ambiguous": true 或 false,
  "ambiguous_reason": "歧义原因（如无歧义则为空字符串）",
  "recommended": "推荐口径中文名",
  "time_expression": "用户提到的时间（今年/上月/本周等，默认今年）",
  "dimension": "用户提到的维度（无则 null）",
  "confidence": 0.0到1.0的浮点数,
  "need_clarify": true 或 false
}}

判断规则：
- confidence < 0.6 或歧义未解决且无历史偏好 → need_clarify=true
- 有历史偏好且匹配当前意图 → 使用历史偏好，ambiguous=false
"""
        raw = self.llm.chat(prompt, system=_SYSTEM)
        result = self._parse_json(raw)

        # 补充 need_clarify 兜底逻辑
        if result.get("ambiguous") and not preference.get(
            result.get("metric_id", "").rsplit("_", 1)[0] if result.get("metric_id") else ""
        ):
            result["need_clarify"] = True

        if result.get("confidence", 1.0) < 0.6:
            result["need_clarify"] = True

        return result

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            # 清理可能的 markdown 代码块
            clean = raw.strip()
            for prefix in ("```json", "```"):
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]
            clean = clean.rstrip("`").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("IntentAgent JSON parse error: %s | raw=%s", e, raw[:200])
            return {
                "metric_id": "article_signed_count",
                "metric_name": "稿件签发通过量",
                "ambiguous": True,
                "ambiguous_reason": "意图解析失败，请重新描述",
                "recommended": "签发量",
                "time_expression": "今年",
                "dimension": None,
                "confidence": 0.3,
                "need_clarify": True,
            }
