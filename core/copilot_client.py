"""
GitHub Copilot API 统一客户端
替代原来的 GeminiClient / GPTClient / ClaudeClient 三个独立客户端
只需要一个 GITHUB_TOKEN，底层通过 model 参数指定不同模型

GitHub Copilot API 端点：
  https://api.githubcopilot.com/chat/completions
  Authorization: Bearer {GITHUB_TOKEN}
  Editor-Version: vscode/1.85.0
  Copilot-Integration-Id: {COPILOT_INTEGRATION_ID}
"""

import os
import httpx
from dataclasses import dataclass, field


@dataclass
class CopilotConfig:
    GITHUB_TOKEN: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    COPILOT_INTEGRATION_ID: str = field(
        default_factory=lambda: os.getenv("COPILOT_INTEGRATION_ID", "article-metric-agent")
    )
    COPILOT_API_URL: str = "https://api.githubcopilot.com/chat/completions"

    # 模型分工（通过同一 API，指定不同 model）
    INTENT_MODEL: str = "gpt-4o"            # GPT 负责意图理解和逻辑校验
    SQL_MODEL: str = "claude-3.5-sonnet"    # Claude 负责 SQL 生成
    SUMMARY_MODEL: str = "gemini-1.5-pro"   # Gemini 负责展示和总结

    # 本地路径
    DB_PATH: str = "local_dev.db"
    VECTOR_STORE_PATH: str = "./vector_store"


class CopilotClient:
    """
    统一的 GitHub Copilot API 客户端
    通过 model 参数在同一接口下调用不同模型
    """

    def __init__(self):
        self.config = CopilotConfig()
        self.headers = {
            "Authorization": f"Bearer {self.config.GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot/1.0.0",
            "Copilot-Integration-Id": self.config.COPILOT_INTEGRATION_ID,
        }

    async def chat(
        self,
        prompt: str,
        model: str = "gpt-4o",
        system: str = None,
        temperature: float = 0.1,
    ) -> str:
        """
        统一调用入口，通过 model 参数选择模型

        model 可选值:
          "gpt-4o"            → 意图识别、逻辑校验（原 GPT）
          "claude-3.5-sonnet" → SQL生成、代码审查（原 Claude）
          "gemini-1.5-pro"    → 展示总结、图表推荐（原 Gemini）
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.config.COPILOT_API_URL,
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Copilot API 调用失败: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise Exception(f"Copilot API 错误: {str(e)}")

    # 便捷方法，保持各 Agent 调用接口不变
    async def chat_with_gpt(self, prompt: str, system: str = None) -> str:
        """意图识别、逻辑校验专用（GPT-4o）"""
        return await self.chat(
            prompt, model=self.config.INTENT_MODEL, system=system, temperature=0.1
        )

    async def chat_with_claude(self, prompt: str, system: str = None) -> str:
        """SQL生成、代码审查专用（Claude）"""
        return await self.chat(
            prompt, model=self.config.SQL_MODEL, system=system, temperature=0.0
        )

    async def chat_with_gemini(self, prompt: str, system: str = None) -> str:
        """展示总结、图表推荐专用（Gemini）"""
        return await self.chat(
            prompt, model=self.config.SUMMARY_MODEL, system=system, temperature=0.3
        )

    async def embed(self, text: str) -> list:
        """文本向量化，用于 RAG 检索"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.githubcopilot.com/embeddings",
                    headers=self.headers,
                    json={"model": "text-embedding-3-small", "input": text},
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            # 降级：返回空向量（维度 1536 对应 text-embedding-3-small 模型），不崩溃
            print(f"Embedding 失败，降级处理: {e}")
            return [0.0] * 1536  # text-embedding-3-small 输出维度为 1536


# 全局单例
copilot = CopilotClient()
