# config.py — 全局配置，读取环境变量，三模型 API Key 及路径配置

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── 模型名称 ──────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-pro"
GPT_MODEL = "gpt-4o"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# ── 路径 ─────────────────────────────────────────────────
DB_PATH = "local_dev.db"
VECTOR_STORE_PATH = "./vector_store"
MEMORY_STORE_PATH = "memory_store.json"
METRICS_DIR = "./metrics"
