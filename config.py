"""
全局配置（统一使用 GitHub Copilot API，只需一个 GITHUB_TOKEN）
"""

import os

# 只需要一个 GITHUB_TOKEN
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
COPILOT_INTEGRATION_ID = os.getenv("COPILOT_INTEGRATION_ID", "article-metric-agent")

# 模型分工配置（都通过 Copilot API 调用）
INTENT_MODEL = "gpt-4o"             # GPT：意图理解、逻辑校验
SQL_MODEL = "claude-3.5-sonnet"     # Claude：SQL生成、代码审查
SUMMARY_MODEL = "gemini-1.5-pro"    # Gemini：展示总结

# 本地路径
DB_PATH = os.getenv("DB_PATH", "local_dev.db")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./vector_store")

# Copilot Extension
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
