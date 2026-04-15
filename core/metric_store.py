# core/metric_store.py — 指标字典加载与向量检索（核心基础设施）

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from config import METRICS_DIR
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MetricStore:
    """加载 metrics/ 目录下的 YAML 指标定义，并提供向量相似度检索"""

    def __init__(self):
        self.metrics: dict[str, dict] = {}
        self.vector_store = VectorStore()
        self._load_metrics()

    def _load_metrics(self) -> None:
        metrics_path = Path(METRICS_DIR)
        if not metrics_path.exists():
            logger.warning("Metrics directory not found: %s", METRICS_DIR)
            return
        for yaml_file in metrics_path.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                metric_id = data.get("metric_id", yaml_file.stem)
                self.metrics[metric_id] = data
                # 构建检索文本：metric_name + alias + 定义
                aliases = data.get("metric_alias", [])
                definition = data.get("definition", {}).get("简述", "")
                search_text = (
                    f"{data.get('metric_name', '')} "
                    + " ".join(aliases)
                    + f" {definition}"
                )
                self.vector_store.add(metric_id, search_text)
                logger.info("Loaded metric: %s", metric_id)
            except Exception as e:
                logger.error("Failed to load %s: %s", yaml_file, e)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """向量相似度检索候选指标，返回 top_k 个指标定义"""
        ids = self.vector_store.search(query, top_k=top_k)
        return [self.metrics[mid] for mid in ids if mid in self.metrics]

    def get(self, metric_id: str) -> Optional[dict]:
        return self.metrics.get(metric_id)

    def all_ids(self) -> list[str]:
        return list(self.metrics.keys())
