# core/metric_store.py
# 职责：加载 metrics/*.yaml，Gemini 向量化，支持语义检索
# 模型：Gemini Embedding（text-embedding-004）

import logging
from pathlib import Path

import yaml

from config import METRICS_DIR
from core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class MetricStore:
    """指标字典加载与向量检索"""

    def __init__(self, metrics_dir: str = METRICS_DIR):
        self._metrics: dict[str, dict] = {}
        self._vector_store = VectorStore()
        self._gemini_client = None  # lazy-initialized to avoid failure when no API key
        self._load_all(metrics_dir)

    # ── 加载 ──────────────────────────────────────────────────

    def _load_all(self, metrics_dir: str) -> None:
        """加载目录下所有 .yaml 指标文件"""
        dir_path = Path(metrics_dir)
        if not dir_path.exists():
            logger.warning("Metrics directory not found: %s", metrics_dir)
            return

        for yaml_file in dir_path.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    metric = yaml.safe_load(f)
                mid = metric.get("metric_id")
                if mid:
                    self._metrics[mid] = metric
                    logger.info("Loaded metric: %s", mid)
            except Exception as e:
                logger.error("Failed to load %s: %s", yaml_file, e)

        # 如果向量库为空，进行首次向量化
        if self._vector_store.count() == 0 and self._metrics:
            self._index_all()

    def _get_gemini(self):
        """懒加载 GeminiClient，避免无 API Key 时启动失败"""
        if self._gemini_client is None:
            from core.llm_client import GeminiClient
            self._gemini_client = GeminiClient()
        return self._gemini_client

    def _index_all(self) -> None:
        """将所有指标向量化写入 ChromaDB（首次运行）"""
        try:
            gemini = self._get_gemini()

            texts, embeddings, metadatas, ids = [], [], [], []
            for mid, metric in self._metrics.items():
                # 拼接用于向量化的文本：名称 + 别名 + 定义 + 示例问题
                alias_str = "、".join(metric.get("metric_alias", []))
                examples = metric.get("examples", [])
                example_qs = "；".join(
                    e.get("question", "") for e in examples[:4]
                )
                definition = metric.get("definition", {})
                text = (
                    f"{metric.get('metric_name', '')} {alias_str} "
                    f"{definition.get('简述', '')} "
                    f"示例：{example_qs}"
                )
                emb = gemini.embed(text)
                if emb:
                    texts.append(text)
                    embeddings.append(emb)
                    metadatas.append({
                        "metric_id": mid,
                        "metric_name": metric.get("metric_name", ""),
                    })
                    ids.append(mid)

            if texts:
                self._vector_store.add_texts(texts, embeddings, metadatas, ids)
                logger.info("Indexed %d metrics into vector store.", len(texts))
        except Exception as e:
            logger.warning("Could not index metrics (no API key?): %s", e)

    # ── 查询 ──────────────────────────────────────────────────

    def search(self, query: str, k: int = 3) -> list[dict]:
        """语义搜索，返回最相似的 k 个指标（含完整定义）"""
        try:
            emb = self._get_gemini().embed(query)
        except Exception:
            emb = []

        if not emb:
            # 降级：关键词匹配
            return self._keyword_search(query, k)

        results = self._vector_store.similarity_search(emb, k)
        enriched = []
        for r in results:
            mid = r["metadata"].get("metric_id", "")
            if mid in self._metrics:
                enriched.append(self._metrics[mid])
        return enriched

    def _keyword_search(self, query: str, k: int) -> list[dict]:
        """关键词降级检索"""
        matched = []
        for metric in self._metrics.values():
            aliases = metric.get("metric_alias", [])
            name = metric.get("metric_name", "")
            all_terms = [name] + aliases
            if any(term in query for term in all_terms):
                matched.append(metric)
        return matched[:k] if matched else list(self._metrics.values())[:k]

    def get(self, metric_id: str) -> dict | None:
        """按 ID 返回完整指标字典"""
        return self._metrics.get(metric_id)

    def all(self) -> list[dict]:
        return list(self._metrics.values())
