# config.py
# 系统配置：读取环境变量，管理三模型 API Keys 及路径

import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM API Keys ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── 模型配置 ──────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-1.5-pro"
GPT_MODEL: str = "gpt-4o"
CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"

# ── 本地路径 ──────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "local_dev.db")
VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./vector_store")
MEMORY_FILE: str = os.getenv("MEMORY_FILE", "user_memory.json")
METRICS_DIR: str = os.getenv("METRICS_DIR", "./metrics")
