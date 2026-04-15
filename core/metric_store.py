"""
core/metric_store.py
指标字典存储 — 使用 Copilot Embedding API 向量化指标内容，支持 RAG 检索
"""

from core.llm_client import copilot_client


class MetricStore:
    """
    指标字典向量存储
    - 存储各指标的名称、口径说明、同义词
    - 通过向量相似度检索最匹配的指标
    """

    # 内置指标字典（正式环境可从 YAML 文件或数据库加载）
    METRICS = [
        {
            "name": "签发量",
            "aliases": ["签发稿量", "签发数", "签发篇数"],
            "description": "经过主编签发审核通过的稿件数量",
            "metric_type": "signed",
        },
        {
            "name": "成品量",
            "aliases": ["成品稿量", "完稿数", "成稿量"],
            "description": "记者完成写作并提交审核的稿件数量",
            "metric_type": "finished",
        },
        {
            "name": "发布量",
            "aliases": ["发稿量", "刊发量", "上线量", "发布稿量"],
            "description": "最终对外发布（上线/刊载）的稿件数量",
            "metric_type": "published",
        },
        {
            "name": "退稿量",
            "aliases": ["退稿数", "打回量", "退回量"],
            "description": "审核未通过被退回给记者的稿件数量",
            "metric_type": "rejected",
        },
    ]

    def __init__(self):
        self._index: list[dict] = []  # {text, embedding, metric}

    async def build_index(self):
        """构建指标向量索引"""
        for metric in self.METRICS:
            text = f"{metric['name']} {' '.join(metric['aliases'])} {metric['description']}"
            embedding = await copilot_client.embed(text)
            self._index.append(
                {"text": text, "embedding": embedding, "metric": metric}
            )

    async def search(self, query: str, top_k: int = 1) -> list[dict]:
        """
        向量检索最匹配的指标

        Args:
            query: 用户查询文本
            top_k: 返回前 k 个结果

        Returns:
            list[dict]: 匹配的指标列表
        """
        if not self._index:
            await self.build_index()

        query_embedding = await copilot_client.embed(query)
        scored = []
        for item in self._index:
            score = _cosine_similarity(query_embedding, item["embedding"])
            scored.append((score, item["metric"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [metric for _, metric in scored[:top_k]]


def _cosine_similarity(a: list, b: list) -> float:
    """计算两个向量的余弦相似度"""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# 全局单例
metric_store = MetricStore()
