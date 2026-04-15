# gemini/summary_renderer.py
# 职责：生成自然语言查询结果总结（HTML 格式）
# 模型：Gemini

import json
import logging

from core.llm_client import GeminiClient

logger = logging.getLogger(__name__)

_SYSTEM = """你是数据分析报告撰写专家，擅长将数据查询结果转化为清晰易懂的中文总结。
生成简洁、专业、有洞察力的 HTML 格式报告片段。"""


class SummaryRenderer:
    """自然语言结果总结（Gemini）"""

    def __init__(self):
        self.llm = GeminiClient()

    def run(
        self,
        data: list[dict],
        metric: dict,
        time_range: dict,
        anomaly: dict | None = None,
    ) -> str:
        """
        生成 HTML 格式总结片段。
        """
        if not data:
            return "<p class='summary-empty'>📭 该时间范围内暂无签发数据，请检查查询条件。</p>"

        value = self._extract_value(data)
        metric_name = metric.get("metric_name", "稿件签发通过量")
        start = time_range.get("start", "")
        end = time_range.get("end", "")

        anomaly_hint = ""
        if anomaly and anomaly.get("is_anomaly"):
            anomaly_hint = f"⚠️ 异常信号：{anomaly.get('reason', '')}。{anomaly.get('suggestion', '')}"

        prompt = f"""
查询结果：
- 指标：{metric_name}
- 时间范围：{start} 至 {end}
- 数据：{json.dumps(data, ensure_ascii=False)}
- 核心数值：{value} 篇
- 异常信息：{anomaly_hint if anomaly_hint else '无异常'}

请生成一段 HTML 格式的数据总结，包含：
1. 核心数字（带单位"篇"）
2. 时间范围说明
3. 如有维度数据，说明各维度分布（最多列出前3名）
4. 异常信号标注（如有）
5. 一条业务建议

HTML 格式要求：
- 使用 <div class="summary-content"> 包裹
- 核心数字用 <span class="highlight-number">X篇</span> 标注
- 异常用 <span class="anomaly-warning"> 标注
- 业务建议用 <div class="business-tip"> 标注
- 简洁，不超过 200 字
"""
        result = self.llm.chat(prompt, system=_SYSTEM)

        if not result or result.startswith("[Gemini Error]"):
            return self._fallback_summary(value, metric_name, start, end, anomaly_hint)

        # 确保有包裹 div
        if "<div class=\"summary-content\">" not in result:
            result = f'<div class="summary-content">{result}</div>'

        return result

    @staticmethod
    def _extract_value(data: list[dict]) -> int:
        if not data:
            return 0
        first = data[0]
        for key in ("signed_count", "count", "total", "value"):
            if key in first:
                return int(first[key]) if first[key] is not None else 0
        vals = list(first.values())
        if vals:
            try:
                return int(vals[0])
            except (TypeError, ValueError):
                pass
        return 0

    @staticmethod
    def _fallback_summary(
        value: int,
        metric_name: str,
        start: str,
        end: str,
        anomaly_hint: str,
    ) -> str:
        anomaly_block = (
            f'<span class="anomaly-warning">⚠️ {anomaly_hint}</span>' if anomaly_hint else ""
        )
        return f"""
<div class="summary-content">
  <p>{start} 至 {end}，{metric_name}共计
    <span class="highlight-number">{value}篇</span>。
  </p>
  {anomaly_block}
  <div class="business-tip">💡 建议结合部门维度进一步分析产能分布。</div>
</div>""".strip()
