# core/llm_client.py
# 职责：统一封装 Gemini、GPT、Claude 三个 LLM 客户端
# 模型：GeminiClient(Gemini), GPTClient(GPT-4o), ClaudeClient(claude-3-5-sonnet)

import logging
import google.generativeai as genai
from openai import OpenAI
import anthropic
from config import (
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    GEMINI_MODEL, GPT_MODEL, CLAUDE_MODEL,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """UI设计、图表推荐、自然语言总结"""

    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)

    def chat(self, prompt: str, system: str = None) -> str:
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error("GeminiClient.chat error: %s", e)
            return f"[Gemini Error] {e}"

    def embed(self, text: str) -> list:
        """向量化，用于 RAG 检索"""
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
            )
            return result["embedding"]
        except Exception as e:
            logger.error("GeminiClient.embed error: %s", e)
            return []


class GPTClient:
    """意图识别、业务逻辑校验、异常归因"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def chat(self, prompt: str, system: str = None) -> str:
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
            return response.choices[0].message.content
        except Exception as e:
            logger.error("GPTClient.chat error: %s", e)
            return f"[GPT Error] {e}"


class ClaudeClient:
    """SQL 生成、代码工程实现、代码审查"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def chat(self, prompt: str, system: str = None) -> str:
        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=system or "你是一个专业的数据分析工程师",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error("ClaudeClient.chat error: %s", e)
            return f"[Claude Error] {e}"
