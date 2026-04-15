"""
意图识别 Agent（使用 GitHub Copilot API / GPT-4o）
负责解析用户自然语言查询，提取统计意图、时间范围、指标口径
"""

import json
from core.copilot_client import copilot

INTENT_SYSTEM_PROMPT = """你是一个专业的稿件指标查询助手，负责解析用户的自然语言查询意图。

请从用户输入中提取以下信息，以 JSON 格式返回：
{
  "caliber": "签发量|发布量|审核通过量",   // 统计口径
  "time_range": {
    "type": "year|month|week|day|custom",
    "start": "YYYY-MM-DD",
    "end": "YYYY-MM-DD"
  },
  "group_by": "department|author|category|null",  // 分组维度
  "filters": {},                                   // 额外过滤条件
  "ambiguous": false,                              // 是否存在歧义
  "ambiguous_options": []                          // 歧义选项列表
}

注意：
- 如果用户说"今年"，计算当前年份的起止日期
- 如果用户说"上个月"，计算上月的起止日期
- 如果存在歧义（如口径不明确），设置 ambiguous=true 并列出选项
- 只返回 JSON，不要添加任何解释"""


class IntentAgent:
    """意图识别 Agent，使用 GPT-4o 进行自然语言理解"""

    async def parse(self, user_query: str) -> dict:
        """
        解析用户查询意图

        Args:
            user_query: 用户的自然语言查询

        Returns:
            包含 caliber, time_range, group_by, filters, ambiguous 等字段的字典
        """
        prompt = f"用户查询：{user_query}"
        response = await copilot.chat_with_gpt(prompt, system=INTENT_SYSTEM_PROMPT)

        try:
            # 尝试提取 JSON
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            # 解析失败时返回默认结构
            return {
                "caliber": "签发量",
                "time_range": {"type": "year", "start": None, "end": None},
                "group_by": None,
                "filters": {},
                "ambiguous": True,
                "ambiguous_options": ["签发量", "发布量", "审核通过量"],
            }
