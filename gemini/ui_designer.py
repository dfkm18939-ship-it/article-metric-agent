# gemini/ui_designer.py — UI 交互方案生成（Gemini）

import logging
from typing import Any

from core.llm_client import GeminiClient

logger = logging.getLogger(__name__)


class UIDesigner:
    """UI 交互方案生成（Gemini 负责）"""

    def __init__(self):
        self.gemini = GeminiClient()

    def design_clarify_dialog(self, ambiguous_query: str, candidates: list[dict]) -> dict[str, Any]:
        """
        为歧义查询生成澄清对话方案。
        返回 {message, options, style}
        """
        candidates_text = "\n".join(
            f"- {c.get('metric_id')}: {c.get('metric_name')} ({', '.join(c.get('metric_alias', [])[:3])})"
            for c in candidates
        )

        prompt = f"""用户输入了一个模糊查询："{ambiguous_query}"

可能匹配的指标：
{candidates_text}

请设计一个友好的澄清对话，帮助用户明确他想查的指标。
返回 JSON：
{{
  "message": "您的问题可能是想查以下指标之一，请选择：",
  "options": [
    {{"key": "A", "label": "稿件签发通过量（签发量）", "metric_id": "article_signed_count"}},
    {{"key": "B", "label": "稿件发布量", "metric_id": "article_published_count"}},
    {{"key": "C", "label": "稿件成品量", "metric_id": "article_finished_count"}}
  ],
  "style": "button_group"
}}"""

        raw = self.gemini.chat(prompt)
        import json, re
        text = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        # 降级返回
        return {
            "message": f'您的问题「{ambiguous_query}」可能对应以下指标，请选择：',
            "options": [
                {"key": "A", "label": "稿件签发通过量（签发量）", "metric_id": "article_signed_count"},
                {"key": "B", "label": "稿件发布量", "metric_id": "article_published_count"},
                {"key": "C", "label": "稿件成品量", "metric_id": "article_finished_count"},
            ],
            "style": "button_group",
        }

    def design_result_layout(self, chart_type: str, has_anomaly: bool) -> dict[str, Any]:
        """返回结果页面的布局方案"""
        return {
            "layout": "card",
            "sections": [
                {"id": "stat", "title": "核心数据", "type": "stat_card"},
                {"id": "chart", "title": "图表展示", "type": chart_type},
                {"id": "summary", "title": "智能总结", "type": "html"},
                {"id": "sql", "title": "查看 SQL", "type": "collapsible_code"},
                *([ {"id": "anomaly", "title": "⚠️ 异常信号", "type": "alert"} ] if has_anomaly else []),
            ],
        }
