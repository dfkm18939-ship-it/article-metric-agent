# core/db_client.py — SQLite 模拟数据库 + 1000 条模拟数据（核心基础设施）

import asyncio
import logging
import random
import sqlite3
import string
from datetime import datetime, timedelta
from typing import Any

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)

DEPARTMENTS = ["新闻部", "评论部", "体育部", "财经部", "科技部"]
ARTICLE_TYPES = ["original"] * 60 + ["reprint"] * 20 + ["special"] * 15 + ["test"] * 5
STATUSES = ["draft"] * 10 + ["finished"] * 15 + ["reviewing"] * 10 + ["signed"] * 50 + ["published"] * 15
AUTHORS = [f"记者{chr(65 + i % 26)}{i // 26 or ''}" for i in range(30)]
COLUMNS = ["头条", "社会", "经济", "体育", "文化", "科技", "评论", "国际", "地方", "专题"]

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31, 23, 59, 59)


def _random_datetime(start: datetime = START_DATE, end: datetime = END_DATE) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def _rand_id(length: int = 12) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fact_article_workflow (
    article_id   TEXT PRIMARY KEY,
    status       TEXT NOT NULL,
    signed_at    DATETIME,
    created_at   DATETIME NOT NULL,
    published_at DATETIME,
    article_type TEXT NOT NULL DEFAULT 'original',
    is_deleted   INTEGER NOT NULL DEFAULT 0,
    dept_name    TEXT,
    author_name  TEXT,
    column_name  TEXT,
    title        TEXT
);
"""


def _generate_rows(n: int = 1000) -> list[tuple]:
    rows = []
    for i in range(n):
        article_id = f"art_{_rand_id()}"
        status = random.choice(STATUSES)
        article_type = random.choice(ARTICLE_TYPES)
        created_at = _random_datetime()
        dept = random.choice(DEPARTMENTS)
        author = random.choice(AUTHORS)
        column = random.choice(COLUMNS)
        title = f"稿件标题_{i + 1}_{dept}"

        signed_at = None
        published_at = None

        if status in ("signed", "published"):
            signed_at = _random_datetime(created_at, min(created_at + timedelta(days=7), END_DATE))
        if status == "published" and signed_at:
            published_at = _random_datetime(signed_at, min(signed_at + timedelta(days=3), END_DATE))

        is_deleted = 1 if random.random() < 0.02 else 0

        rows.append((
            article_id,
            status,
            signed_at.strftime("%Y-%m-%d %H:%M:%S") if signed_at else None,
            created_at.strftime("%Y-%m-%d %H:%M:%S"),
            published_at.strftime("%Y-%m-%d %H:%M:%S") if published_at else None,
            article_type,
            is_deleted,
            dept,
            author,
            column,
            title,
        ))
    return rows


def init_db(db_path: str = DB_PATH) -> None:
    """同步初始化数据库（首次启动时调用）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    cursor.execute("SELECT COUNT(*) FROM fact_article_workflow")
    count = cursor.fetchone()[0]
    if count == 0:
        rows = _generate_rows(1000)
        cursor.executemany(
            """INSERT OR IGNORE INTO fact_article_workflow
               (article_id, status, signed_at, created_at, published_at,
                article_type, is_deleted, dept_name, author_name, column_name, title)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
        logger.info("Inserted %d mock rows into fact_article_workflow", len(rows))
    conn.close()


async def execute_query(sql: str) -> list[dict[str, Any]]:
    """异步执行 SQL，返回 list of dict"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error("execute_query error: %s | SQL: %s", e, sql)
        raise
