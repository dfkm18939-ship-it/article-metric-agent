# main.py
# 职责：FastAPI 应用入口，初始化数据库，挂载路由
# 模型：无（路由在 claude/api_server.py 中定义）

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from claude.api_server import router
from core.db_client import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 应用初始化 ────────────────────────────────────────────────
app = FastAPI(
    title="数据指标智能查询助手",
    description="多模型协作的稿件指标智能查询系统（GPT + Gemini + Claude）",
    version="1.0.0",
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# 挂载 API 路由
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    logger.info("Starting up article-metric-agent...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回主页面"""
    try:
        with open("web/index.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>web/index.html not found</h1>", status_code=404)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
