# core/memory_agent.py — 用户偏好与对话上下文记忆（核心基础设施）

import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

from config import MEMORY_STORE_PATH

logger = logging.getLogger(__name__)


class MemoryAgent:
    """基于本地 JSON 文件的用户偏好与对话历史管理"""

    def __init__(self, store_path: str = MEMORY_STORE_PATH):
        self.store_path = store_path
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("MemoryAgent load error: %s", e)
        return {}

    def _save(self) -> None:
        try:
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("MemoryAgent save error: %s", e)

    def get_context(self, user_id: str) -> dict:
        """获取用户上下文（角色、偏好、历史）"""
        return self._data.get(user_id, {
            "role": "普通编辑",
            "preferences": {},
            "history": [],
        })

    def get_preference(self, user_id: str, metric_group: str) -> Optional[str]:
        """获取用户在某指标组的偏好 metric_id"""
        ctx = self.get_context(user_id)
        return ctx.get("preferences", {}).get(metric_group)

    def update(self, user_id: str, intent: dict) -> None:
        """更新用户历史记录和偏好"""
        if user_id not in self._data:
            self._data[user_id] = {"role": "普通编辑", "preferences": {}, "history": []}

        # 记录历史
        history_entry = {
            "query": intent.get("original_query", ""),
            "metric_id": intent.get("metric_id", ""),
            "timestamp": datetime.now().isoformat(),
        }
        self._data[user_id].setdefault("history", []).append(history_entry)

        # 最多保留最近 50 条历史
        self._data[user_id]["history"] = self._data[user_id]["history"][-50:]

        # 更新偏好
        if intent.get("metric_id") and not intent.get("ambiguous"):
            metric_id = intent["metric_id"]
            # 使用指标 ID 前缀作为 group key
            group_key = "article_metric"
            self._data[user_id].setdefault("preferences", {})[group_key] = metric_id

        self._save()

    def set_role(self, user_id: str, role: str) -> None:
        """设置用户角色"""
        if user_id not in self._data:
            self._data[user_id] = {"role": role, "preferences": {}, "history": []}
        else:
            self._data[user_id]["role"] = role
        self._save()
