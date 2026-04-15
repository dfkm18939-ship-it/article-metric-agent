"""
config.py
统一配置文件 — GitHub Copilot API 单 Token 方案
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    # GitHub Token（需要 copilot 权限）
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

    # Copilot API 基础地址
    COPILOT_API_BASE: str = os.getenv(
        "COPILOT_API_BASE", "https://api.githubcopilot.com"
    )

    # 三个任务对应的模型（通过 Copilot API 指定）
    INTENT_MODEL: str = "gpt-4o"            # 意图识别用 GPT-4o
    SQL_MODEL: str = "claude-3.5-sonnet"    # SQL生成用 Claude
    SUMMARY_MODEL: str = "gemini-1.5-pro"   # 展示总结用 Gemini
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # 向量化

    # 数据库 / 向量存储路径
    DB_PATH: str = os.getenv("DB_PATH", "local_dev.db")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./vector_store")

    # Web 服务配置
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))


config = Config()
