"""
main.py
FastAPI 应用入口 — 提供 Web UI 和 Copilot Extension 两个入口
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from config import config
from core.orchestrator import Orchestrator
from copilot_extension.handler import handle_copilot_request
from copilot_extension.middleware import verify_github_signature

app = FastAPI(
    title="稿件指标智能查询系统",
    description="GitHub Copilot API 驱动的多模型协作稿件指标查询助手",
    version="1.0.0",
)

orchestrator = Orchestrator()


# ---------------------------------------------------------------------------
# Copilot Extension 路由
# ---------------------------------------------------------------------------


@app.post("/agent")
async def copilot_agent(request: Request):
    """
    GitHub Copilot Extension 入口
    用户在 GitHub 中使用 @article-metric-agent 时触发
    """
    await verify_github_signature(request)
    return await handle_copilot_request(request)


@app.get("/copilot/health")
async def copilot_health():
    """Extension 健康检查"""
    return {"status": "ok", "extension": "article-metric-agent", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Web UI 路由
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    """Web UI 首页"""
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>稿件指标智能查询</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
  <div class="bg-white rounded-2xl shadow-lg p-8 w-full max-w-2xl">
    <h1 class="text-2xl font-bold text-gray-800 mb-2">📊 稿件指标智能查询</h1>
    <p class="text-gray-500 text-sm mb-6">
      由 GitHub Copilot API 驱动（GPT-4o · Claude 3.5 · Gemini 1.5）
    </p>

    <div id="chat" class="space-y-3 mb-4 min-h-[120px] max-h-80 overflow-y-auto
                           bg-gray-50 rounded-xl p-4 text-sm text-gray-700">
      <p class="text-gray-400">请输入查询，例如：<em>今年签发了多少稿件？</em></p>
    </div>

    <div class="flex gap-2">
      <input id="input" type="text" placeholder="输入查询..."
             class="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm
                    focus:outline-none focus:ring-2 focus:ring-blue-400"
             onkeydown="if(event.key==='Enter') send()" />
      <button onclick="send()"
              class="bg-blue-500 hover:bg-blue-600 text-white px-5 py-2 rounded-lg
                     text-sm font-medium transition-colors">
        查询
      </button>
    </div>
  </div>

  <script>
    async function send() {
      const input = document.getElementById('input');
      const chat = document.getElementById('chat');
      const query = input.value.trim();
      if (!query) return;
      input.value = '';

      chat.innerHTML += `<p><strong>你：</strong>${escapeHtml(query)}</p>`;

      const res = await fetch('/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query})
      });
      const data = await res.json();
      chat.innerHTML += `<p><strong>助手：</strong>${escapeHtml(data.summary || data.message || JSON.stringify(data))}</p>`;
      chat.scrollTop = chat.scrollHeight;
    }

    function escapeHtml(text) {
      return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/query")
async def query(request: Request):
    """Web UI 查询接口"""
    body = await request.json()
    user_query = body.get("query", "")
    try:
        result = await orchestrator.run(user_query=user_query)
        return result
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"type": "error", "message": "查询处理失败，请稍后重试。"},
        )


# ---------------------------------------------------------------------------
# 启动入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=True,
    )
