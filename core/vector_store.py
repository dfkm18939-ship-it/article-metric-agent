# core/vector_store.py — 向量库（chromadb 本地存储）（核心基础设施）

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings

from config import VECTOR_STORE_PATH

logger = logging.getLogger(__name__)


class VectorStore:
    """基于 ChromaDB 的本地向量存储，用于指标相似度检索"""

    COLLECTION_NAME = "metrics"

    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(
                path=VECTOR_STORE_PATH,
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.error("VectorStore init error: %s", e)
            self.client = None
            self.collection = None

    def add(self, doc_id: str, text: str) -> None:
        """添加文档到向量库（使用 ChromaDB 内置嵌入）"""
        if self.collection is None:
            return
        try:
            # ChromaDB 默认使用 all-MiniLM-L6-v2 进行嵌入
            self.collection.upsert(
                ids=[doc_id],
                documents=[text],
            )
        except Exception as e:
            logger.error("VectorStore.add error for %s: %s", doc_id, e)

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """相似度搜索，返回匹配的 doc_id 列表"""
        if self.collection is None:
            return []
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, max(1, self.collection.count())),
            )
            ids = results.get("ids", [[]])[0]
            return ids
        except Exception as e:
            logger.error("VectorStore.search error: %s", e)
            return []
