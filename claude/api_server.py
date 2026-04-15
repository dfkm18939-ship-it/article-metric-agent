# claude/api_server.py — FastAPI 路由和接口定义（Claude）

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from core.orchestrator import Orchestrator
from core.memory_agent import MemoryAgent
from core.metric_store import MetricStore

logger = logging.getLogger(__name__)
router = APIRouter()

# 单例
_orchestrator: Optional[Orchestrator] = None
_memory: Optional[MemoryAgent] = None
_metric_store: Optional[MetricStore] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def get_memory() -> MemoryAgent:
    global _memory
    if _memory is None:
        _memory = MemoryAgent()
    return _memory


def get_metric_store() -> MetricStore:
    global _metric_store
    if _metric_store is None:
        _metric_store = MetricStore()
    return _metric_store


# ── Pydantic 模型 ──────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


class ClarifyRequest(BaseModel):
    choice: str
    user_id: str = "anonymous"
    original_query: str


# ── 路由 ────────────────────────────────────────────────────────

@router.post("/api/query")
async def api_query(req: QueryRequest):
    """完整查询流程"""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="查询不能为空")
    try:
        result = await get_orchestrator().run(req.query.strip(), req.user_id)
        return result
    except Exception as e:
        logger.error("api_query error: %s", e)
        raise HTTPException(status_code=500, detail="查询处理失败，请稍后重试")


@router.post("/api/clarify")
async def api_clarify(req: ClarifyRequest):
    """用户选择澄清选项后继续查询"""
    if not req.choice or not req.original_query:
        raise HTTPException(status_code=400, detail="choice 和 original_query 不能为空")
    try:
        result = await get_orchestrator().handle_clarify(
            req.choice, req.user_id, req.original_query
        )
        return result
    except Exception as e:
        logger.error("api_clarify error: %s", e)
        raise HTTPException(status_code=500, detail="澄清处理失败，请稍后重试")


@router.get("/api/metrics")
async def api_metrics():
    """返回所有指标列表"""
    store = get_metric_store()
    metrics = []
    for mid in store.all_ids():
        m = store.get(mid)
        if m:
            metrics.append({
                "metric_id": m.get("metric_id"),
                "metric_name": m.get("metric_name"),
                "metric_alias": m.get("metric_alias", []),
                "definition": m.get("definition", {}).get("简述", ""),
            })
    return {"metrics": metrics}


@router.get("/api/history/{user_id}")
async def api_history(user_id: str):
    """返回用户查询历史"""
    ctx = get_memory().get_context(user_id)
    return {
        "user_id": user_id,
        "role": ctx.get("role", "普通编辑"),
        "history": ctx.get("history", []),
        "preferences": ctx.get("preferences", {}),
    }


@router.get("/", response_class=HTMLResponse)
async def root():
    """返回主页面"""
    html_path = Path(__file__).parent.parent / "web" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>稿件指标智能助手</h1><p>web/index.html not found</p>")
