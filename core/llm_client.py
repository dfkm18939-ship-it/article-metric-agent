# core/llm_client.py — 三模型统一客户端
# GeminiClient（Gemini）、GPTClient（GPT）、ClaudeClient（Claude）

import json
import logging
from typing import Optional

from google import genai
from google.genai import types as genai_types
import openai
import anthropic

from config import (
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    GEMINI_MODEL, GPT_MODEL, CLAUDE_MODEL,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini 客户端 — 负责 UI 设计、图表推荐、文字总结（Gemini）"""

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def chat(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            contents = prompt
            config = None
            if system:
                config = genai_types.GenerateContentConfig(
                    system_instruction=system,
                )
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            logger.error("GeminiClient.chat error: %s", e)
            return f"[Gemini Error] {e}"

    def embed(self, text: str) -> list[float]:
        try:
            result = self.client.models.embed_content(
                model="models/text-embedding-004",
                contents=text,
            )
            return result.embeddings[0].values if result.embeddings else []
        except Exception as e:
            logger.error("GeminiClient.embed error: %s", e)
            return []


class GPTClient:
    """GPT 客户端 — 负责意图识别、业务逻辑校验、异常归因（GPT）"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)

    def chat(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0.1,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("GPTClient.chat error: %s", e)
            return f"[GPT Error] {e}"


class ClaudeClient:
    """Claude 客户端 — 负责 SQL 生成、代码工程实现（Claude）"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def chat(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            kwargs: dict = {
                "model": CLAUDE_MODEL,
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            logger.error("ClaudeClient.chat error: %s", e)
            return f"[Claude Error] {e}"
