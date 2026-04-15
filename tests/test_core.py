"""
基础功能测试
测试各模块的导入和基本功能（不依赖真实 API）
"""

import pytest
import asyncio
import json


# ──────────────────────────────────────────────
# CopilotClient 测试
# ──────────────────────────────────────────────

def test_copilot_config_defaults():
    """CopilotConfig 默认值测试"""
    from core.copilot_client import CopilotConfig
    cfg = CopilotConfig()
    assert cfg.COPILOT_API_URL == "https://api.githubcopilot.com/chat/completions"
    assert cfg.COPILOT_INTEGRATION_ID == "article-metric-agent"
    assert cfg.INTENT_MODEL == "gpt-4o"
    assert cfg.SQL_MODEL == "claude-3.5-sonnet"
    assert cfg.SUMMARY_MODEL == "gemini-1.5-pro"


def test_copilot_client_headers():
    """CopilotClient 请求头包含必要字段"""
    from core.copilot_client import CopilotClient
    client = CopilotClient()
    assert "Authorization" in client.headers
    assert "Copilot-Integration-Id" in client.headers
    assert client.headers["Copilot-Integration-Id"] == "article-metric-agent"
    assert client.headers["Editor-Version"] == "vscode/1.85.0"


# ──────────────────────────────────────────────
# Config 测试
# ──────────────────────────────────────────────

def test_config_imports():
    """config.py 所有配置项可正常导入"""
    import config
    assert hasattr(config, "GITHUB_TOKEN")
    assert hasattr(config, "INTENT_MODEL")
    assert hasattr(config, "SQL_MODEL")
    assert hasattr(config, "SUMMARY_MODEL")
    assert hasattr(config, "DB_PATH")
    # 确保已移除独立 API Key（改造验证）
    assert not hasattr(config, "OPENAI_API_KEY")
    assert not hasattr(config, "ANTHROPIC_API_KEY")
    assert not hasattr(config, "GEMINI_API_KEY")


# ──────────────────────────────────────────────
# IntentAgent 降级处理测试（无需 API）
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_intent_agent_parse_fallback(monkeypatch):
    """IntentAgent 在 JSON 解析失败时返回合理默认值"""
    from gpt.intent_agent import IntentAgent

    async def mock_chat_with_gpt(prompt, system=None):
        return "无法解析的响应"  # 模拟 JSON 解析失败

    from core import copilot_client
    monkeypatch.setattr(copilot_client.copilot, "chat_with_gpt", mock_chat_with_gpt)

    agent = IntentAgent()
    result = await agent.parse("今年签发了多少稿件")

    assert "caliber" in result
    assert "time_range" in result
    assert "ambiguous" in result


# ──────────────────────────────────────────────
# SQLGenerator 降级处理测试（无需 API）
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sql_generator_fallback(monkeypatch):
    """SQLGenerator 在 JSON 解析失败时生成默认 SQL"""
    from claude.sql_generator import SQLGenerator

    async def mock_chat_with_claude(prompt, system=None):
        return "无法解析的响应"

    from core import copilot_client
    monkeypatch.setattr(copilot_client.copilot, "chat_with_claude", mock_chat_with_claude)

    gen = SQLGenerator()
    intent = {
        "caliber": "签发量",
        "time_range": {"type": "year", "start": "2024-01-01", "end": "2024-12-31"},
        "group_by": None,
    }
    result = await gen.generate(intent)
    assert "sql" in result
    assert "SELECT" in result["sql"].upper()


# ──────────────────────────────────────────────
# CodeReviewer 测试（无需 API）
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_code_reviewer_safe_sql(monkeypatch):
    """CodeReviewer 正常 SQL 应通过审查"""
    from claude.code_reviewer import CodeReviewer

    async def mock_chat_with_claude(prompt, system=None):
        return json.dumps({
            "safe": True,
            "issues": [],
            "severity": "none",
            "approved_sql": "SELECT COUNT(*) FROM articles WHERE status='approved'",
        })

    from core import copilot_client
    monkeypatch.setattr(copilot_client.copilot, "chat_with_claude", mock_chat_with_claude)

    reviewer = CodeReviewer()
    result = await reviewer.review("SELECT COUNT(*) FROM articles WHERE status='approved'")
    assert result["safe"] is True
    assert result["severity"] == "none"


@pytest.mark.asyncio
async def test_code_reviewer_fallback(monkeypatch):
    """CodeReviewer 在 JSON 解析失败时不阻断流程"""
    from claude.code_reviewer import CodeReviewer

    async def mock_chat_with_claude(prompt, system=None):
        return "无法解析"

    from core import copilot_client
    monkeypatch.setattr(copilot_client.copilot, "chat_with_claude", mock_chat_with_claude)

    sql = "SELECT COUNT(*) FROM articles"
    reviewer = CodeReviewer()
    result = await reviewer.review(sql)
    assert result["safe"] is True
    assert result["approved_sql"] == sql


# ──────────────────────────────────────────────
# Orchestrator 时间范围解析测试（无需 API）
# ──────────────────────────────────────────────

def test_resolve_time_range_year():
    from datetime import date
    from core.orchestrator import _resolve_time_range

    result = _resolve_time_range({"type": "year"})
    today = date.today()
    assert result["start"] == str(date(today.year, 1, 1))
    assert result["end"] == str(date(today.year, 12, 31))


def test_resolve_time_range_month():
    from datetime import date
    from core.orchestrator import _resolve_time_range

    result = _resolve_time_range({"type": "month"})
    today = date.today()
    assert result["start"].startswith(str(today.year))
    assert result["type"] == "month"


# ──────────────────────────────────────────────
# 数据库执行测试（使用本地 DB）
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_db_query_executes():
    """Orchestrator._execute_query 能正确执行 SQL"""
    import os
    if not os.path.exists("local_dev.db"):
        pytest.skip("local_dev.db 不存在，跳过数据库测试")

    from core.orchestrator import Orchestrator
    orch = Orchestrator()
    result = await orch._execute_query(
        "SELECT COUNT(*) AS total FROM articles WHERE status='approved'"
    )
    assert "total" in result
    assert isinstance(result["total"], int)
    assert result["total"] >= 0


# ──────────────────────────────────────────────
# Copilot Extension middleware 测试
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_signature_missing_header():
    """缺少签名头时应抛出 401"""
    from fastapi import HTTPException
    from copilot_extension.middleware import verify_github_signature
    from unittest.mock import AsyncMock, MagicMock

    request = MagicMock()
    request.headers = {}
    request.body = AsyncMock(return_value=b"test body")

    with pytest.raises(HTTPException) as exc_info:
        await verify_github_signature(request, "secret")
    assert exc_info.value.status_code == 401
