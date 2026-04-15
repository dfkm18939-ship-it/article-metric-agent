# core/vector_store.py
# 职责：ChromaDB 本地向量库，支持文本向量化存储和相似度检索
# 无 LLM 调用（embedding 由 MetricStore 通过 Gemini 生成）

import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings

from config import VECTOR_STORE_PATH

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB 本地持久化向量库"""

    COLLECTION_NAME = "metrics"

    def __init__(self, path: str = VECTOR_STORE_PATH):
        Path(path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready at %s (collection=%s, items=%d)",
            path,
            self.COLLECTION_NAME,
            self._collection.count(),
        )

    # ── Write ─────────────────────────────────────────────────

    def add_texts(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str] | None = None,
    ) -> None:
        """批量写入文本、向量和元数据"""
        if not texts:
            return
        if ids is None:
            # 用 metadata 中的 metric_id 作为文档 ID，保证幂等
            ids = [m.get("metric_id", f"doc_{i}") for i, m in enumerate(metadatas)]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        logger.info("VectorStore: upserted %d items.", len(texts))

    # ── Read ──────────────────────────────────────────────────

    def similarity_search(
        self,
        query_embedding: list[float],
        k: int = 3,
    ) -> list[dict]:
        """返回 k 个最相似文档，每条格式 {document, metadata, distance}"""
        if not query_embedding:
            return []
        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, max(1, self._collection.count())),
                include=["documents", "metadatas", "distances"],
            )
            items = []
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                items.append({"document": doc, "metadata": meta, "distance": dist})
            return items
        except Exception as e:
            logger.error("VectorStore.similarity_search error: %s", e)
            return []

    def count(self) -> int:
        return self._collection.count()
