"""
copilot_extension/middleware.py
验证来自 GitHub 的 Copilot Extension 请求签名
确保请求真实来自 GitHub，防止伪造
"""

import os

from fastapi import HTTPException, Request


async def verify_github_signature(request: Request) -> bool:
    """
    验证 GitHub Copilot Extension 请求签名

    GitHub 会在请求头中包含：
    - X-GitHub-Public-Key-Identifier: 公钥ID
    - X-GitHub-Public-Key-Signature: 请求签名
    """
    # 本地开发阶段可跳过验证
    if os.getenv("SKIP_SIGNATURE_VERIFY", "false").lower() == "true":
        return True

    signature = request.headers.get("X-GitHub-Public-Key-Signature")
    key_id = request.headers.get("X-GitHub-Public-Key-Identifier")

    if not signature or not key_id:
        raise HTTPException(status_code=401, detail="缺少签名头")

    # 生产环境：使用 cryptography 库实现 ECDSA 签名验证
    # 参考：https://docs.github.com/en/copilot/building-copilot-extensions/
    #        building-a-copilot-agent-for-your-copilot-extension/
    #        configuring-your-copilot-agent-to-communicate-with-github
    #
    # 示例（需从 GitHub 获取公钥后实现）：
    #   from cryptography.hazmat.primitives.asymmetric import ec
    #   from cryptography.hazmat.primitives import hashes, serialization
    #   public_key = fetch_github_public_key(key_id)
    #   public_key.verify(signature_bytes, body, ec.ECDSA(hashes.SHA256()))
    raise HTTPException(status_code=401, detail="生产环境必须实现签名验证")
