"""
异常分析 Agent（使用 GitHub Copilot API / GPT-4o）
负责检测数据中的异常波动并生成分析报告
"""

import json
from core.copilot_client import copilot

ANOMALY_SYSTEM_PROMPT = """你是一个数据异常检测专家，擅长分析稿件生产指标的异常波动。

给定时间序列数据，请识别异常并以 JSON 格式返回：
{
  "has_anomaly": true|false,
  "anomalies": [
    {
      "date": "YYYY-MM-DD",
      "value": 数值,
      "expected_range": [下限, 上限],
      "severity": "low|medium|high",
      "possible_reason": "可能原因"
    }
  ],
  "trend": "increasing|decreasing|stable|fluctuating",
  "summary": "整体趋势说明"
}"""


class AnomalyAnalyzer:
    """异常分析 Agent，使用 GPT-4o 检测数据异常"""

    async def analyze(self, time_series_data: list, metric_name: str = "签发量") -> dict:
        """
        分析时间序列数据中的异常

        Args:
            time_series_data: [{"date": "...", "value": ...}, ...]
            metric_name: 指标名称

        Returns:
            异常分析结果字典
        """
        prompt = f"""
指标名称：{metric_name}
时间序列数据：{json.dumps(time_series_data, ensure_ascii=False)}

请检测数据中的异常波动。
"""
        response = await copilot.chat_with_gpt(prompt, system=ANOMALY_SYSTEM_PROMPT)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "has_anomaly": False,
                "anomalies": [],
                "trend": "stable",
                "summary": "数据分析完成，未发现明显异常。",
            }
