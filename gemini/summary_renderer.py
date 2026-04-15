"""
结果总结渲染 Agent（使用 GitHub Copilot API / Gemini 1.5 Pro）
负责将查询结果转化为易读的 HTML 展示内容
"""

import json
from core.copilot_client import copilot

SUMMARY_RENDERER_SYSTEM_PROMPT = """你是一个数据可视化和报告撰写专家，擅长将稿件指标数据转化为清晰易读的 HTML 摘要。

给定查询结果数据，生成简洁的 HTML 摘要，要求：
1. 突出核心数字（用 <strong> 标签）
2. 包含环比/同比变化（如数据充足）
3. 使用中文，语言简洁专业
4. 结构清晰，便于在对话界面中显示

返回 JSON 格式：
{
  "summary_html": "<strong>XX</strong> 篇稿件...",
  "key_metrics": [{"label": "总签发量", "value": "1234", "unit": "篇"}],
  "insight": "核心洞察一句话"
}"""


class SummaryRenderer:
    """结果总结渲染 Agent，使用 Gemini 1.5 Pro"""

    async def render(self, query_result: dict, intent: dict) -> dict:
        """
        将查询结果渲染为 HTML 摘要

        Args:
            query_result: 数据库查询结果
            intent: 查询意图

        Returns:
            包含 summary_html, key_metrics, insight 字段的字典
        """
        prompt = f"""
查询意图：{json.dumps(intent, ensure_ascii=False)}
查询结果：{json.dumps(query_result, ensure_ascii=False)}

请生成数据摘要展示内容。
"""
        response = await copilot.chat_with_gemini(prompt, system=SUMMARY_RENDERER_SYSTEM_PROMPT)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            # 提取关键数值
            total = query_result.get("total", query_result.get("count", 0))
            caliber = intent.get("caliber", "签发量")
            return {
                "summary_html": f"共 <strong>{total}</strong> 篇{caliber}。",
                "key_metrics": [{"label": caliber, "value": str(total), "unit": "篇"}],
                "insight": f"该时间段内共有 {total} 篇{caliber}。",
            }
