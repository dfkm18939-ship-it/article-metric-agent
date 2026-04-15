# gemini/summary_renderer.py — 自然语言结果总结渲染，输出 HTML 片段（Gemini）

import logging
from typing import Any

from core.llm_client import GeminiClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的数据分析师和文案专家，擅长将数字结果转化为易读的中文报告。
你的输出必须是 HTML 片段，使用 <strong> 高亮关键数字，使用 <span class="anomaly"> 标注异常。
不要输出 ```html 代码块标记，直接输出 HTML 内容。"""


class SummaryRenderer:
    """自然语言结果总结渲染（Gemini 负责）"""

    def __init__(self):
        self.gemini = GeminiClient()

    def render(
        self,
        data: list[dict],
        intent: dict,
        time_range: dict,
        anomaly_info: dict = None,
    ) -> str:
        """
        将查询结果转化为 HTML 格式的自然语言总结。
        返回完整 HTML 片段字符串。
        """
        if not data:
            return "<p>暂无数据，请检查查询条件或时间范围。</p>"

        metric_name = intent.get("metric_name", "签发量")
        time_expr = intent.get("time_expression", "今年")
        dimension = intent.get("dimension")
        start = time_range.get("start", "")
        end = time_range.get("end", "")

        # 提取核心数值
        total = 0
        if len(data) == 1 and not dimension:
            total = list(data[0].values())[0]
        elif data:
            # 取所有数值列的总和
            for row in data:
                for v in row.values():
                    if isinstance(v, (int, float)):
                        total += v

        anomaly_text = ""
        if anomaly_info and anomaly_info.get("has_anomaly"):
            anomalies = anomaly_info.get("anomalies", [])
            anomaly_text = f"\n数据异常情况：{anomalies}\n归因分析：{anomaly_info.get('interpretation', '')}"

        dimension_desc = ""
        if dimension and len(data) > 1:
            top = data[0]
            keys = list(top.keys())
            dim_val = top.get(keys[0], "")
            count_val = top.get(keys[-1], 0)
            dimension_desc = f"\n按{dimension}分组，最高的是 {dim_val}（{count_val}篇）"

        prompt = f"""请为以下数据查询结果生成一段自然语言总结报告（HTML 格式）：

指标：{metric_name}
时间范围：{time_expr}（{start} 至 {end}）
查询结果：{data[:10]}
总量：{total}篇
{dimension_desc}
{anomaly_text}

要求：
1. 第一行是核心结论一句话（用 <p class="conclusion"> 包裹）
2. 用 <strong> 标签高亮关键数字
3. 如有同环比数据，描述增减趋势
4. 如有异常，用 <span class="anomaly">⚠️ 异常信号</span> 标注
5. 最后给出 1-2 条业务建议（用 <ul class="suggestions"> 包裹）
6. 直接输出 HTML，不要 markdown 代码块

HTML 输出："""

        html = self.gemini.chat(prompt, system=SYSTEM_PROMPT)
        # 去掉可能的 markdown 代码块
        import re
        html = re.sub(r"```(?:html)?", "", html).strip().strip("`").strip()
        return html

    def render_fallback(self, data: list[dict], intent: dict, time_range: dict) -> str:
        """降级渲染：当 Gemini 不可用时，生成基础 HTML"""
        metric_name = intent.get("metric_name", "签发量")
        time_expr = intent.get("time_expression", "今年")
        total = 0
        if data:
            for row in data:
                for v in row.values():
                    if isinstance(v, (int, float)):
                        total += v

        return f"""<p class="conclusion">{time_expr}{metric_name}共 <strong>{total:,}</strong> 篇。</p>
<p>统计时间：{time_range.get('start', '')} 至 {time_range.get('end', '')}</p>
<ul class="suggestions">
  <li>请关注各部门签发量分布，了解产能差异。</li>
</ul>"""
