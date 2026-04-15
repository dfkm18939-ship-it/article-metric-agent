# gpt/anomaly_analyzer.py
# 职责：数据异常归因分析
# 模型：GPT-4o

import json
import logging

from core.llm_client import GPTClient

logger = logging.getLogger(__name__)

_SYSTEM = """你是数据分析专家，擅长诊断新闻媒体生产数据异常。
只返回 JSON，不要任何额外内容。"""


class AnomalyAnalyzer:
    """数据异常归因（GPT）"""

    def __init__(self):
        self.llm = GPTClient()

    def run(self, data: list[dict], metric: dict) -> dict:
        """
        检测数据是否异常，给出归因和建议。
        返回：{is_anomaly: bool, reason: str, suggestion: str}
        """
        thresholds = metric.get("business_rules", {}).get("异常阈值", {})
        daily_min = thresholds.get("日最小值", 10)
        daily_max = thresholds.get("日最大值", 500)

        # 提取数值
        value = self._extract_value(data)

        # 本地快速检测
        if value is None:
            return {
                "is_anomaly": True,
                "reason": "查询结果为空，可能无签发数据",
                "suggestion": "请确认时间范围内是否有签发记录，或检查权限设置",
            }

        prompt = f"""
查询结果数据：{json.dumps(data, ensure_ascii=False)}
指标名称：{metric.get('metric_name', '')}
异常阈值（日）：最小 {daily_min}，最大 {daily_max}
查询到的总量：{value}

请判断数据是否异常，分析可能原因，给出排查建议。

返回 JSON：
{{
  "is_anomaly": true 或 false,
  "reason": "异常原因描述（正常则为空字符串）",
  "suggestion": "排查建议（正常则为空字符串）"
}}

异常场景参考：
- 数量为 0：可能是数据未同步、时间范围无数据、或条件过严
- 数量异常高：可能是测试数据污染、日期范围过宽
- 数量远低于均值：可能是节假日、系统故障、权限限制
"""
        raw = self.llm.chat(prompt, system=_SYSTEM)
        return self._parse_json(raw)

    @staticmethod
    def _extract_value(data: list[dict]) -> int | None:
        if not data:
            return None
        first = data[0]
        for key in ("signed_count", "count", "total", "value"):
            if key in first:
                return int(first[key]) if first[key] is not None else None
        vals = list(first.values())
        if vals:
            try:
                return int(vals[0])
            except (TypeError, ValueError):
                pass
        return None

    @staticmethod
    def _parse_json(raw: str) -> dict:
        try:
            clean = raw.strip().lstrip("```json").lstrip("```").rstrip("`").strip()
            return json.loads(clean)
        except Exception as e:
            logger.error("AnomalyAnalyzer JSON parse error: %s", e)
            return {"is_anomaly": False, "reason": "", "suggestion": ""}
