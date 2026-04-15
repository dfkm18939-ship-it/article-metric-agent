# claude/api_server.py
# 职责：FastAPI 路由定义（由 main.py 挂载）
# 模型：全部通过 Orchestrator 调用

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from core.memory_agent import MemoryAgent
from core.metric_store import MetricStore
from core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = Orchestrator()
memory = MemoryAgent()
metric_store = MetricStore()


# ── 请求/响应模型 ─────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user"


class ClarifyRequest(BaseModel):
    choice: str          # "A" / "B" / "C"
    user_id: str = "default_user"
    original_query: str


# ── 路由 ──────────────────────────────────────────────────────

@router.post("/api/query")
async def query(request: QueryRequest):
    """主查询接口"""
    try:
        result = await orchestrator.run(
            user_query=request.query,
            user_id=request.user_id,
        )
        return result
    except Exception as e:
        logger.error("POST /api/query error: %s", e)
        return {"type": "error", "message": "查询处理失败，请稍后重试"}


@router.post("/api/clarify")
async def clarify(request: ClarifyRequest):
    """澄清选项处理接口"""
    try:
        result = await orchestrator.run_clarify(
            choice=request.choice,
            user_id=request.user_id,
            original_query=request.original_query,
        )
        return result
    except Exception as e:
        logger.error("POST /api/clarify error: %s", e)
        return {"type": "error", "message": "澄清处理失败，请稍后重试"}


@router.get("/api/metrics")
async def get_metrics():
    """返回所有可用指标列表"""
    metrics = metric_store.all()
    return {
        "metrics": [
            {
                "metric_id": m.get("metric_id"),
                "metric_name": m.get("metric_name"),
                "alias": m.get("metric_alias", []),
                "definition": m.get("definition", {}).get("简述", ""),
            }
            for m in metrics
        ]
    }


@router.get("/api/history/{user_id}")
async def get_history(user_id: str):
    """用户查询历史"""
    history = memory.get_history(user_id)
    return {"user_id": user_id, "history": history}
