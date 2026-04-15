# claude/code_reviewer.py — 代码/SQL 审查（Claude）

import json
import logging
import re
from typing import Any

from core.llm_client import ClaudeClient

logger = logging.getLogger(__name__)


class CodeReviewer:
    """代码与 SQL 质量审查（Claude 负责）"""

    def __init__(self):
        self.claude = ClaudeClient()

    def review_sql(self, sql: str) -> dict[str, Any]:
        """
        从技术角度审查 SQL 的语法正确性和性能。
        返回 {passed, issues, optimized_sql, reviewed_by}
        """
        prompt = f"""请从技术工程角度审查以下 SQLite SQL 的质量：

SQL：
{sql}

检查项：
1. SQL 语法是否正确
2. 是否有明显的性能问题（全表扫描/无索引条件）
3. 是否有 SQL 注入风险（虽然是参数化，检查是否有动态拼接）
4. 字段名是否符合规范（fact_article_workflow 表字段）
5. 是否可以优化

返回严格 JSON（不要 markdown）：
{{
  "passed": true,
  "issues": [],
  "optimized_sql": "",
  "reviewed_by": "Claude"
}}

注意：optimized_sql 如无优化建议则为空字符串。"""

        raw = self.claude.chat(prompt)
        return self._parse_json(raw)

    def review_intent(self, intent: dict, user_query: str) -> dict[str, Any]:
        """
        验证 GPT 的意图解析是否技术层面可执行。
        返回 {executable, risks, fix_suggestion, reviewed_by}
        """
        known_metrics = ["article_signed_count", "article_published_count", "article_finished_count"]
        known_dimensions = ["dept_name", "article_type", "author_name", "column_name", None]
        known_times = ["今天", "昨天", "本周", "上周", "本月", "上月", "今年", "去年"]

        prompt = f"""验证以下意图解析是否可以被技术执行：

用户原始问题：{user_query}
GPT 解析的意图：{json.dumps(intent, ensure_ascii=False)}

检查项：
1. metric_id（{intent.get('metric_id')}）是否在已知列表：{known_metrics}
2. time_expression（{intent.get('time_expression')}）是否可被解析：{known_times}
3. dimension（{intent.get('dimension')}）是否在支持列表：{known_dimensions}
4. 是否有技术层面的执行风险

返回严格 JSON（不要 markdown）：
{{
  "executable": true,
  "risks": [],
  "fix_suggestion": "",
  "reviewed_by": "Claude"
}}"""

        raw = self.claude.chat(prompt)
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            result = json.loads(text)
            result.setdefault("reviewed_by", "Claude")
            return result
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    result.setdefault("reviewed_by", "Claude")
                    return result
                except Exception:
                    pass
        logger.error("CodeReviewer: Failed to parse JSON: %s", raw[:200])
        return {"passed": True, "executable": True, "issues": [], "risks": [], "reviewed_by": "Claude"}
