# gpt/logic_validator.py — 业务规则校验，验证 SQL 是否符合业务逻辑（GPT）

import json
import logging
import re
from typing import Any

from core.llm_client import GPTClient

logger = logging.getLogger(__name__)


class LogicValidator:
    """业务规则校验器（GPT 负责）"""

    def __init__(self):
        self.gpt = GPTClient()

    def validate_sql_business_logic(self, sql: str, metric: dict) -> dict[str, Any]:
        """
        GPT 从业务逻辑角度审查 SQL 是否符合指标定义。
        返回 {passed, issues, suggestion, reviewed_by}
        """
        definition = metric.get("definition", {})
        business_rules = metric.get("business_rules", {})
        calc = metric.get("calculation", {})

        prompt = f"""请从业务逻辑角度严格审查以下 SQL 是否符合指标定义：

指标名称：{metric.get('metric_name', '')}
指标简述：{definition.get('简述', '')}
统计方式：{calc.get('统计方式', '')}
核心条件：
  - status 应为 'signed'
  - 时间字段应使用 signed_at（不是 created_at 或 published_at）
  - 排除测试稿件：article_type != 'test'
  - 排除已删除：is_deleted = 0
  - 去重：COUNT(DISTINCT article_id)

待审查 SQL：
{sql}

请检查以下项目：
1. status 条件是否正确（应为 status = 'signed'）
2. 时间字段是否使用 signed_at
3. 是否排除了测试稿件（article_type != 'test'）
4. 是否排除了已删除（is_deleted = 0）
5. 是否使用了 COUNT(DISTINCT article_id) 去重

返回严格 JSON（不要 markdown）：
{{
  "passed": true,
  "issues": [],
  "suggestion": "",
  "reviewed_by": "GPT"
}}"""

        raw = self.gpt.chat(prompt)
        return self._parse_json(raw)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            result = json.loads(text)
            result.setdefault("reviewed_by", "GPT")
            return result
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    result.setdefault("reviewed_by", "GPT")
                    return result
                except Exception:
                    pass
        logger.error("LogicValidator: Failed to parse JSON: %s", raw[:200])
        return {"passed": False, "issues": ["GPT审查解析失败"], "suggestion": "请重试", "reviewed_by": "GPT"}
