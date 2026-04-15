"""
GitHub Copilot Extension 核心处理器
接收来自 GitHub Copilot 平台的 SSE 请求，返回流式响应

Copilot Extension 请求格式：
  POST /agent
  Headers:
    X-GitHub-Token: {user_github_token}
    Content-Type: application/json
  Body: {
    "messages": [{"role": "user", "content": "@article-metric-agent 今年签发了多少稿件"}],
    "copilot_thread_id": "...",
    "agent": {"slug": "article-metric-agent"}
  }

响应格式：Server-Sent Events (SSE)
  data: {"id":"...","choices":[{"delta":{"content":"..."}}]}
"""

import json
import asyncio
from fastapi import Request
from fastapi.responses import StreamingResponse
from core.orchestrator import Orchestrator

orchestrator = Orchestrator()


async def handle_copilot_extension(request: Request):
    """
    Copilot Extension 主处理函数
    解析用户消息 → 调用 Orchestrator → 流式返回结果
    """
    body = await request.json()
    messages = body.get("messages", [])

    # 提取用户最后一条消息
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            # 去掉 @mention 前缀
            user_message = user_message.replace("@article-metric-agent", "").strip()
            break

    # 提取 GitHub Token 作为用户 ID（取哈希值，不存储原始 Token）
    github_token = request.headers.get("X-GitHub-Token", "anonymous")
    user_id = f"gh_{hash(github_token) % 100000}"

    async def generate():
        try:
            # 调用 Orchestrator 处理查询
            result = await orchestrator.run(user_message, user_id)

            # 构建响应文本
            if result["type"] == "clarify":
                response_text = "您的问题涉及多个统计口径，请确认：\n\n"
                for opt in result.get("options", []):
                    response_text += f"- {opt}\n"
            elif result["type"] == "result":
                response_text = "## 📊 查询结果\n\n"
                response_text += (
                    result.get("summary_html", "")
                    .replace("<strong>", "**")
                    .replace("</strong>", "**")
                    .replace("<br>", "\n")
                )
                response_text += f"\n\n**口径：** {result.get('caliber', '签发量')}"
                time_range = result.get("time_range", {})
                response_text += (
                    f"\n**时间范围：** {time_range.get('start', '')} 至 {time_range.get('end', '')}"
                )
                response_text += (
                    f"\n\n<details>\n<summary>查看 SQL</summary>\n\n"
                    f"```sql\n{result.get('sql', '')}\n```\n</details>"
                )
            else:
                response_text = f"查询出现问题：{result.get('message', '未知错误')}"

            # 流式输出（SSE 格式）
            words = response_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                sse_data = {
                    "id": f"chatcmpl-{i}",
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": chunk}, "index": 0}],
                }
                yield f"data: {json.dumps(sse_data)}\n\n"
                await asyncio.sleep(0.02)

            # 结束信号
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_sse = {
                "id": "error",
                "object": "chat.completion.chunk",
                "choices": [{"delta": {"content": f"处理失败：{str(e)}"}, "index": 0}],
            }
            yield f"data: {json.dumps(error_sse)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
