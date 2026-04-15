"""
Claude 模块的 FastAPI 路由（查询 API）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"


class QueryResponse(BaseModel):
    type: str
    message: str = ""
    summary_html: str = ""
    sql: str = ""
    caliber: str = ""
    time_range: dict = {}
    options: list = []
    chart: dict = {}


@router.post("/query", response_model=QueryResponse)
async def query_metrics(request: QueryRequest):
    """
    自然语言查询稿件指标

    接收用户自然语言问题，经过多模型协作处理后返回结构化结果。
    """
    try:
        from core.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        result = await orchestrator.run(request.query, request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def list_metrics():
    """列出所有支持的指标口径"""
    return {
        "metrics": [
            {
                "name": "签发量",
                "description": "审核通过的稿件数量",
                "field": "approved_at",
                "status_filter": "approved",
            },
            {
                "name": "发布量",
                "description": "已发布的稿件数量",
                "field": "published_at",
                "status_filter": "published",
            },
            {
                "name": "审核通过量",
                "description": "审核通过（含已发布）的稿件数量",
                "field": "approved_at",
                "status_filter": "approved,published",
            },
        ]
    }
