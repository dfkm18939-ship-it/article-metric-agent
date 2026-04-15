"""
稿件指标智能助手 + GitHub Copilot Extension
主应用入口
"""

import json
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from claude.api_server import router as api_router
from copilot_extension.handler import handle_copilot_extension
from copilot_extension.middleware import verify_github_signature

app = FastAPI(
    title="稿件指标智能助手 + Copilot Extension",
    description="多模型协作的稿件指标智能查询系统，支持 GitHub Copilot Extension",
    version="2.0.0",
)

# 原有 Web API 路由
app.include_router(api_router, prefix="/api")


# Copilot Extension 路由（核心新增）
@app.post("/agent")
async def copilot_agent(request: Request):
    """
    GitHub Copilot Extension 入口
    GitHub 平台会将用户的 @article-metric-agent 消息 POST 到此路由
    """
    # 验证签名（生产环境开启）
    webhook_secret = os.getenv("WEBHOOK_SECRET", "")
    if webhook_secret:
        await verify_github_signature(request, webhook_secret)

    return await handle_copilot_extension(request)


# 健康检查（Copilot Extension 注册时需要）
@app.get("/health")
async def health():
    return {"status": "ok", "service": "article-metric-agent"}


# Extension Manifest
@app.get("/.well-known/copilot-agent-manifest.json")
async def manifest():
    manifest_path = os.path.join(
        os.path.dirname(__file__), "copilot_extension", "manifest.json"
    )
    with open(manifest_path) as f:
        return json.load(f)


# Web UI
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    with open(html_path) as f:
        return f.read()


# 挂载静态资源
static_dir = os.path.join(os.path.dirname(__file__), "web", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
