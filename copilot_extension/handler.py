"""
copilot_extension/handler.py
GitHub Copilot Extension 主处理器

用户在 GitHub 中输入：
  @article-metric-agent 今年签发了多少稿件？

本处理器接收请求，调用 Orchestrator，流式返回结果
"""

import asyncio
import json
import re

from fastapi import Request
from fastapi.responses import StreamingResponse

from core.orchestrator import Orchestrator

orchestrator = Orchestrator()


async def handle_copilot_request(request: Request) -> StreamingResponse:
    """
    处理来自 GitHub Copilot 的 Agent 请求

    GitHub Copilot Extension 协议：
    - 请求格式：JSON（消息列表）
    - 响应格式：SSE 流式输出
    - 消息格式遵循 OpenAI Chat Completions 协议
    """

    body = await request.json()

    # 解析用户消息
    messages = body.get("messages", [])
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        user_message = item.get("text", "").strip()
                        break
            else:
                user_message = content.strip()
            break

    # 提取用户标识
    user_login = body.get("copilot_thread_id", "default_user")

    async def generate_response():
        """生成 SSE 格式的流式响应"""
        try:
            # 调用 Orchestrator 执行完整查询流程
            result = await orchestrator.run(
                user_query=user_message,
                user_id=user_login,
            )

            if result["type"] == "clarify":
                clarify_text = f"{result['message']}\n\n"
                for option in result.get("options", []):
                    clarify_text += f"- {option}\n"
                async for chunk in _stream_text(clarify_text):
                    yield chunk

            elif result["type"] == "result":
                summary = _format_result_for_copilot(result)
                async for chunk in _stream_text(summary):
                    yield chunk

            else:
                error_text = f"查询遇到问题：{result.get('message', '未知错误')}"
                async for chunk in _stream_text(error_text):
                    yield chunk

        except Exception:
            error_msg = "系统内部错误，请稍后重试。"
            async for chunk in _stream_text(error_msg):
                yield chunk

        # 发送结束标记
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_text(text: str):
    """将文本转换为 SSE 流式格式（打字机效果）"""
    chunk_size = 10
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        data = {
            "choices": [
                {
                    "delta": {"content": chunk, "role": "assistant"},
                    "finish_reason": None,
                    "index": 0,
                }
            ]
        }
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.01)


def _format_result_for_copilot(result: dict) -> str:
    """将查询结果格式化为 Markdown（适合在 GitHub 界面显示）"""
    lines = []

    caliber = result.get("caliber", "签发量")
    time_range = result.get("time_range", {})
    start = time_range.get("start", "")
    end = time_range.get("end", "")

    lines.append(f"## 📊 {caliber} 查询结果")
    lines.append(f"**统计口径**：{caliber} | **时间范围**：{start} 至 {end}")
    lines.append("")

    data = result.get("data", [])
    if data:
        if len(data) == 1 and "count" in data[0]:
            count = data[0]["count"]
            lines.append(f"### 🔢 {count:,} 篇")
        else:
            lines.append("| 维度 | 数量 |")
            lines.append("|------|------|")
            for row in data:
                dim_val = list(row.values())[0] if row else "-"
                count = list(row.values())[-1] if row else 0
                lines.append(f"| {dim_val} | {count:,} 篇 |")

    lines.append("")

    summary = result.get("summary", "")
    if summary:
        clean_summary = re.sub(r"<[^>]+>", "", summary)
        lines.append(f"**分析**：{clean_summary}")
        lines.append("")

    sql = result.get("sql", "")
    if sql:
        lines.append("<details>")
        lines.append("<summary>查看 SQL</summary>")
        lines.append("")
        lines.append("```sql")
        lines.append(sql)
        lines.append("```")
        lines.append("</details>")

    return "\n".join(lines)
