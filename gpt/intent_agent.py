# gpt/intent_agent.py — 意图识别 + 歧义判断（GPT）

import json
import logging
import re
from typing import Any

from core.llm_client import GPTClient
from core.metric_store import MetricStore
from core.memory_agent import MemoryAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的新闻媒体数据指标理解专家。
你的任务是从用户的自然语言查询中识别其意图，映射到正确的指标、时间范围和维度。
你必须严格返回 JSON 格式，不要有任何额外说明。"""


class IntentAgent:
    """意图识别 + 歧义判断（GPT 负责）"""

    def __init__(self):
        self.gpt = GPTClient()
        self.metric_store = MetricStore()
        self.memory = MemoryAgent()

    async def recognize(self, user_query: str, user_id: str = "anonymous") -> dict[str, Any]:
        """识别用户意图，返回结构化意图 JSON"""
        # 1. 向量检索候选指标（top 3）
        candidates = self.metric_store.search(user_query, top_k=3)

        # 2. 读取用户历史偏好
        context = self.memory.get_context(user_id)
        user_preference = self.memory.get_preference(user_id, "article_metric")

        # 3. 构建候选指标摘要
        candidates_text = ""
        for c in candidates:
            aliases = ", ".join(c.get("metric_alias", []))
            candidates_text += f"- {c['metric_id']}: {c['metric_name']}（别名: {aliases}）\n"

        if not candidates_text:
            candidates_text = "- article_signed_count: 稿件签发通过量（别名: 签发量, 签发稿件数, 过审稿件数, 生产稿件数）\n"

        prompt = f"""用户查询：{user_query}

用户角色：{context.get('role', '普通编辑')}
用户历史偏好：{user_preference or '无'}

候选指标：
{candidates_text}

已知歧义映射规则：
- "生产了多少" → article_signed_count
- "有多少稿件" → article_signed_count（歧义，需澄清）
- "发布了多少" → article_published_count
- "写了多少" → article_finished_count
- "上线了多少" → article_published_count

支持的时间表达：今天/昨天/本周/上周/本月/上月/今年/去年
支持的业务维度：dept_name（部门）、article_type（稿件类型）、author_name（作者）、column_name（栏目）

请分析用户意图，返回严格的 JSON（不要有 markdown 代码块）：
{{
  "metric_id": "article_signed_count",
  "metric_name": "稿件签发通过量",
  "ambiguous": false,
  "ambiguous_reason": "",
  "recommended": "签发量",
  "time_expression": "今年",
  "dimension": null,
  "confidence": 0.95,
  "need_clarify": false,
  "clarify_options": []
}}

说明：
- confidence < 0.6 或 ambiguous=true 且无历史偏好时，need_clarify=true
- clarify_options 在 need_clarify=true 时填入 A/B/C 三个选项供用户选择
- dimension 使用字段名（如 dept_name），无维度时为 null"""

        raw = self.gpt.chat(prompt, system=SYSTEM_PROMPT)
        return self._parse_json(raw, user_query)

    def _parse_json(self, raw: str, user_query: str) -> dict[str, Any]:
        """带容错处理的 JSON 解析"""
        # 去掉 markdown 代码块
        text = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 {...}
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        logger.error("IntentAgent: Failed to parse JSON from GPT: %s", raw[:200])
        # 降级：返回默认意图，需要澄清
        return {
            "metric_id": "article_signed_count",
            "metric_name": "稿件签发通过量",
            "ambiguous": True,
            "ambiguous_reason": "无法解析模型返回",
            "recommended": "签发量",
            "time_expression": "今年",
            "dimension": None,
            "confidence": 0.3,
            "need_clarify": True,
            "clarify_options": [
                {"key": "A", "label": "稿件签发通过量（签发量）"},
                {"key": "B", "label": "稿件发布量"},
                {"key": "C", "label": "稿件成品量"},
            ],
        }
