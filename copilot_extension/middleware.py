"""
GitHub Copilot Extension 签名验证中间件
验证请求来自合法的 GitHub Copilot 平台
"""

import hmac
import hashlib
from fastapi import Request, HTTPException


async def verify_github_signature(request: Request, webhook_secret: str):
    """验证 GitHub Webhook 签名"""
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not signature:
        raise HTTPException(status_code=401, detail="缺少签名头")

    body = await request.body()
    expected = "sha256=" + hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="签名验证失败")

    return True
