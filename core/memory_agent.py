# core/memory_agent.py
# 职责：用户偏好与对话上下文记忆（本地 JSON 文件存储）
# 无 LLM 调用

import json
import logging
from pathlib import Path

from config import MEMORY_FILE

logger = logging.getLogger(__name__)


class MemoryAgent:
    """本地 JSON 文件存储用户记忆"""

    def __init__(self, memory_file: str = MEMORY_FILE):
        self._file = Path(memory_file)
        self._data: dict = self._load()

    # ── 持久化 ────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._file.exists():
            try:
                with open(self._file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load memory file: %s", e)
        return {}

    def _save(self) -> None:
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save memory file: %s", e)

    # ── 公共接口 ──────────────────────────────────────────────

    def get_context(self, user_id: str) -> dict:
        """返回用户上下文：{role, preference, history}"""
        user = self._data.setdefault(user_id, {
            "role": "editor",
            "preference": {},
            "history": [],
        })
        return user

    def update(self, user_id: str, intent: dict) -> None:
        """根据本次意图更新偏好和历史"""
        user = self.get_context(user_id)

        # 更新口径偏好
        metric_id = intent.get("metric_id", "")
        if metric_id:
            metric_group = metric_id.rsplit("_", 1)[0]  # e.g. "article_signed"
            user["preference"][metric_group] = metric_id

        # 追加历史（保留最近 20 条）
        history_entry = {
            "metric_id": metric_id,
            "time_expression": intent.get("time_expression", ""),
            "dimension": intent.get("dimension"),
        }
        history: list = user.setdefault("history", [])
        history.append(history_entry)
        if len(history) > 20:
            user["history"] = history[-20:]

        self._data[user_id] = user
        self._save()

    def get_preference(self, user_id: str, metric_group: str) -> str | None:
        """返回该用户对某指标组的口径偏好（metric_id）"""
        user = self.get_context(user_id)
        return user.get("preference", {}).get(metric_group)

    def get_history(self, user_id: str) -> list[dict]:
        return self.get_context(user_id).get("history", [])
