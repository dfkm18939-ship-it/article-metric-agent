"""
图表推荐 Agent（使用 GitHub Copilot API / Gemini 1.5 Pro）
负责根据数据特征推荐最合适的图表类型并生成 ECharts 配置
"""

import json
from core.copilot_client import copilot

CHART_ADVISOR_SYSTEM_PROMPT = """你是一个数据可视化专家，擅长为稿件指标数据推荐最合适的图表并生成 ECharts 配置。

根据数据特征（时序/分类/对比/分布），推荐图表类型并生成配置。

返回 JSON 格式：
{
  "chart_type": "line|bar|pie|scatter|heatmap",
  "reason": "推荐理由",
  "echarts_option": {
    "title": {"text": "图表标题"},
    "xAxis": {...},
    "yAxis": {...},
    "series": [...]
  }
}

ECharts 配置要求：
- 使用中文标签
- 颜色方案：专业蓝系（#1890ff, #36cbcb, #4ecb73）
- 时序数据用折线图
- 分类对比用柱状图
- 占比分析用饼图"""


class ChartAdvisor:
    """图表推荐 Agent，使用 Gemini 1.5 Pro"""

    async def advise(self, query_result: dict, intent: dict) -> dict:
        """
        根据查询结果推荐图表类型和配置

        Args:
            query_result: 数据库查询结果
            intent: 查询意图

        Returns:
            包含 chart_type, reason, echarts_option 字段的字典
        """
        prompt = f"""
查询意图：{json.dumps(intent, ensure_ascii=False)}
查询结果：{json.dumps(query_result, ensure_ascii=False)}

请推荐最合适的图表并生成 ECharts 配置。
"""
        response = await copilot.chat_with_gemini(prompt, system=CHART_ADVISOR_SYSTEM_PROMPT)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            caliber = intent.get("caliber", "签发量")
            total = query_result.get("total", 0)
            return {
                "chart_type": "bar",
                "reason": "数据量较少，柱状图展示更直观",
                "echarts_option": {
                    "title": {"text": f"{caliber}统计"},
                    "xAxis": {"type": "category", "data": ["汇总"]},
                    "yAxis": {"type": "value"},
                    "series": [
                        {
                            "type": "bar",
                            "data": [total],
                            "itemStyle": {"color": "#1890ff"},
                        }
                    ],
                },
            }
