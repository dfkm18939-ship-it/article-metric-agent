"""
core/llm_client.py
统一的 GitHub Copilot API 客户端
通过指定 model 参数调用不同的底层模型
所有模型通过同一个 GITHUB_TOKEN 访问
"""

import httpx
import json
import logging
from config import config

logger = logging.getLogger(__name__)


class CopilotClient:
    """
    GitHub Copilot API 统一客户端
    支持多模型：gpt-4o / claude-3.5-sonnet / gemini-1.5-pro
    """

    def __init__(self):
        self.token = config.GITHUB_TOKEN
        self.base_url = config.COPILOT_API_BASE
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Copilot-Integration-Id": "article-metric-agent",
            "Editor-Version": "article-metric-agent/1.0",
        }

    async def chat(
        self,
        prompt: str,
        model: str = "gpt-4o",
        system: str = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """
        调用 Copilot Chat Completions API

        Args:
            prompt: 用户提问
            model: 模型名称，可选 gpt-4o / claude-3.5-sonnet / gemini-1.5-pro
            system: 系统提示词
            temperature: 温度（0.0~1.0）
            max_tokens: 最大 token 数

        Returns:
            str: 模型回复文本
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Copilot API HTTP错误: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise Exception(f"Copilot API 调用失败: {str(e)}")

    async def chat_with_gpt(self, prompt: str, system: str = None) -> str:
        """使用 GPT-4o（意图识别/业务逻辑校验）"""
        return await self.chat(
            prompt, model=config.INTENT_MODEL, system=system, temperature=0.1
        )

    async def chat_with_claude(self, prompt: str, system: str = None) -> str:
        """使用 Claude 3.5 Sonnet（SQL生成/代码审查）"""
        return await self.chat(
            prompt, model=config.SQL_MODEL, system=system, temperature=0.1
        )

    async def chat_with_gemini(self, prompt: str, system: str = None) -> str:
        """使用 Gemini 1.5 Pro（UI展示/结果总结）"""
        return await self.chat(
            prompt, model=config.SUMMARY_MODEL, system=system, temperature=0.3
        )

    async def embed(self, text: str) -> list:
        """
        文本向量化（用于指标字典 RAG 检索）
        使用 text-embedding-3-small 模型
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json={
                        "model": config.EMBEDDING_MODEL,
                        "input": text,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            # 降级：返回空向量，不崩溃
            logger.warning("Embedding 失败，使用降级方案: %s", str(e))
            return [0.0] * 1536

    async def stream_chat(
        self, prompt: str, model: str = "gpt-4o", system: str = None
    ):
        """
        流式对话（用于 Copilot Extension 实时输出）

        Yields:
            str: 流式文本片段
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0]["delta"]
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                            except (json.JSONDecodeError, KeyError):
                                continue
        except Exception as e:
            yield f"[流式输出错误: {str(e)}]"


# 全局单例
copilot_client = CopilotClient()
