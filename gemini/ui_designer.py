# gemini/ui_designer.py
# 职责：当 need_clarify=true 时生成澄清交互方案（HTML）
# 模型：Gemini

import logging

from core.llm_client import GeminiClient

logger = logging.getLogger(__name__)

_SYSTEM = """你是 UI/UX 设计师，专注于数据查询澄清交互设计。
生成简洁的 HTML 澄清方案，包含选项按钮，不要使用任何 CSS 框架，使用 class 名。"""

CALIBER_OPTIONS = [
    {
        "label": "A",
        "metric_id": "article_signed_count",
        "name": "签发量（推荐）",
        "desc": "通过全部审核流程并签发确认的稿件数",
        "recommended": True,
    },
    {
        "label": "B",
        "metric_id": "article_finished_count",
        "name": "成品量",
        "desc": "已完稿但可能尚未正式签发的稿件数",
        "recommended": False,
    },
    {
        "label": "C",
        "metric_id": "article_published_count",
        "name": "发布量",
        "desc": "已在平台上线发布的稿件数",
        "recommended": False,
    },
]


class UIDesigner:
    """澄清交互方案生成（Gemini）"""

    def __init__(self):
        self.llm = GeminiClient()

    def run(self, intent: dict) -> str:
        """生成澄清选项 HTML 片段"""
        ambiguous_reason = intent.get("ambiguous_reason", "您的问题涉及多个统计口径")
        user_query = intent.get("_original_query", "")

        prompt = f"""
用户问题："{user_query}"
歧义原因：{ambiguous_reason}

为以下三个口径选项生成澄清交互 HTML：
{[f"{o['label']}. {o['name']}：{o['desc']}" for o in CALIBER_OPTIONS]}

HTML 要求：
- 外层 <div class="clarify-container">
- 提示文字 <p class="clarify-hint">
- 每个选项 <button class="clarify-btn" data-metric-id="..." data-label="A/B/C">
- 推荐项加 class="clarify-btn recommended"
- 推荐项加 <span class="recommend-badge">推荐</span>
- 不使用任何外部 CSS 框架

只返回 HTML，不要解释。
"""
        result = self.llm.chat(prompt, system=_SYSTEM)

        if not result or result.startswith("[Gemini Error]"):
            return self._fallback_html(ambiguous_reason)

        return result

    @staticmethod
    def _fallback_html(hint: str) -> str:
        buttons = ""
        for opt in CALIBER_OPTIONS:
            rec_class = " recommended" if opt["recommended"] else ""
            rec_badge = '<span class="recommend-badge">推荐</span>' if opt["recommended"] else ""
            buttons += f"""
  <button class="clarify-btn{rec_class}"
          data-metric-id="{opt['metric_id']}"
          data-label="{opt['label']}">
    <strong>{opt['label']}. {opt['name']}</strong>{rec_badge}
    <br><small>{opt['desc']}</small>
  </button>"""

        return f"""
<div class="clarify-container">
  <p class="clarify-hint">🤔 您的问题「{hint}」涉及多个统计口径，请确认您想查询的是：</p>
  {buttons}
</div>""".strip()
