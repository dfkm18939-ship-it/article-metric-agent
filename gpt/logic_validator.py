# gpt/logic_validator.py
# 职责：验证 Claude 生成的 SQL 是否符合业务规则
# 模型：GPT-4o

import json
import logging
import re

from core.llm_client import GPTClient

logger = logging.getLogger(__name__)

_SYSTEM = """你是数据 SQL 审查专家，专注于验证稿件指标 SQL 的业务合规性。
只返回 JSON，不要任何额外内容。"""


class LogicValidator:
    """业务规则 SQL 校验（GPT）"""

    def __init__(self):
        self.llm = GPTClient()

    def run(self, sql: str, metric: dict) -> dict:
        """
        验证 SQL 是否符合业务规则。
        返回：{passed: bool, issues: list[str], suggestion: str}
        """
        # 先做快速本地检查
        local_issues = self._local_check(sql)

        prompt = f"""
请审查以下 SQL 是否符合稿件签发通过量（article_signed_count）的业务规则：

SQL:
{sql}

指标定义：
{json.dumps(metric.get('calculation', {}), ensure_ascii=False, indent=2)}

必须满足的规则：
1. WHERE 条件中必须有 status = 'signed'
2. 时间字段必须使用 signed_at（不能用 created_at）
3. 必须排除 article_type = 'test'
4. 必须有 is_deleted = 0 条件
5. 必须使用 COUNT(DISTINCT article_id) 统计

已发现的本地问题：{local_issues}

返回 JSON：
{{
  "passed": true 或 false,
  "issues": ["问题1", "问题2"],
  "suggestion": "修改建议（如果 passed=true 则为空字符串）"
}}
"""
        raw = self.llm.chat(prompt, system=_SYSTEM)
        result = self._parse_json(raw)

        # 合并本地检查结果
        if local_issues:
            result["passed"] = False
            result.setdefault("issues", [])
            for issue in local_issues:
                if issue not in result["issues"]:
                    result["issues"].append(issue)

        return result

    # ── 本地快速检查 ──────────────────────────────────────────

    @staticmethod
    def _local_check(sql: str) -> list[str]:
        """无需 LLM 的规则检查"""
        issues = []
        sql_upper = sql.upper()

        if "STATUS = 'SIGNED'" not in sql_upper and 'STATUS="SIGNED"' not in sql_upper:
            issues.append("缺少 status = 'signed' 条件")
        if "SIGNED_AT" not in sql_upper:
            issues.append("时间字段应使用 signed_at")
        if "CREATED_AT" in sql_upper and "SIGNED_AT" not in sql_upper:
            issues.append("不应使用 created_at 作为签发时间字段")
        if "IS_DELETED" not in sql_upper:
            issues.append("缺少 is_deleted = 0 条件")
        if "ARTICLE_TYPE" not in sql_upper or (
            "!= 'TEST'" not in sql_upper and "<> 'TEST'" not in sql_upper
        ):
            issues.append("缺少排除 article_type = 'test' 条件")
        return issues

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("`").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("LogicValidator JSON parse error: %s", e)
            return {"passed": False, "issues": ["GPT 返回解析失败"], "suggestion": "请重新生成 SQL"}
