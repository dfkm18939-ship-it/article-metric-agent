# gpt/anomaly_analyzer.py — 数据异常归因分析（GPT）

import logging
from typing import Any

from core.llm_client import GPTClient

logger = logging.getLogger(__name__)


class AnomalyAnalyzer:
    """数据异常归因分析（GPT 负责）"""

    def __init__(self):
        self.gpt = GPTClient()

    def analyze(self, data: list[dict], metric: dict, time_range: dict) -> dict[str, Any]:
        """
        分析数据是否存在异常，给出业务层面解读。
        返回 {has_anomaly, anomalies, interpretation, suggestions}
        """
        if not data:
            return {
                "has_anomaly": False,
                "anomalies": [],
                "interpretation": "暂无数据",
                "suggestions": [],
            }

        # 提取数值
        values = []
        for row in data:
            for v in row.values():
                if isinstance(v, (int, float)):
                    values.append(v)

        thresholds = metric.get("business_rules", {}).get("异常阈值", {})
        daily_min = thresholds.get("日最小值", 10)
        daily_max = thresholds.get("日最大值", 500)
        drop_pct = thresholds.get("环比下降预警", 30)

        prompt = f"""作为数据分析专家，请分析以下稿件指标数据是否存在异常：

指标：{metric.get('metric_name', '稿件签发通过量')}
时间范围：{time_range}
数据：{data[:20]}  # 最多展示前20条

异常阈值参考：
- 日最小值：{daily_min}
- 日最大值：{daily_max}
- 环比下降预警阈值：{drop_pct}%

请判断：
1. 数据中是否有明显异常（过高/过低/骤降/骤增）
2. 可能的业务原因（节假日/重大事件/系统问题等）
3. 是否需要人工介入

返回 JSON（不要 markdown）：
{{
  "has_anomaly": false,
  "anomalies": [],
  "interpretation": "数据总体正常，...",
  "suggestions": []
}}"""

        raw = self.gpt.chat(prompt)
        import re, json
        text = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        logger.error("AnomalyAnalyzer: Failed to parse JSON")
        return {
            "has_anomaly": False,
            "anomalies": [],
            "interpretation": "异常分析暂不可用",
            "suggestions": [],
        }
