# core/db_client.py
# 职责：SQLite 本地数据库客户端，模拟稿件生产数据（1000条）
# 无 LLM 调用

import asyncio
import logging
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)

# ── 常量 ─────────────────────────────────────────────────────
STATUSES = ["draft", "finished", "signed", "published"]
STATUS_WEIGHTS = [0.10, 0.20, 0.45, 0.25]  # draft, finished, signed, published
ARTICLE_TYPES = ["original", "reprint", "special", "test"]
TYPE_WEIGHTS = [0.55, 0.25, 0.15, 0.05]
DEPARTMENTS = ["要闻部", "社会部", "财经部", "科技部", "体育部", "娱乐部"]
AUTHORS = [f"记者{chr(65+i)}" for i in range(20)]
COLUMNS = ["头版", "国内", "国际", "财经", "科技", "体育", "文化", "评论"]


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def init_db(db_path: str = DB_PATH) -> None:
    """同步初始化数据库（首次启动时调用）"""
    path = Path(db_path)
    if path.exists():
        logger.info("Database already exists at %s, skipping init.", db_path)
        return

    logger.info("Initializing SQLite database at %s ...", db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fact_article_workflow (
            article_id   TEXT PRIMARY KEY,
            status       TEXT NOT NULL,
            signed_at    TEXT,
            created_at   TEXT NOT NULL,
            article_type TEXT NOT NULL DEFAULT 'original',
            is_deleted   INTEGER NOT NULL DEFAULT 0,
            dept_name    TEXT,
            author_name  TEXT,
            column_name  TEXT
        )
    """)

    # 生成 1000 条模拟数据，时间跨度近两年
    now = datetime.now()
    two_years_ago = now - timedelta(days=730)
    rows = []
    for i in range(1, 1001):
        article_id = f"ART{i:05d}"
        status = random.choices(STATUSES, STATUS_WEIGHTS)[0]
        art_type = random.choices(ARTICLE_TYPES, TYPE_WEIGHTS)[0]
        is_deleted = 1 if random.random() < 0.03 else 0
        dept = random.choice(DEPARTMENTS)
        author = random.choice(AUTHORS)
        column = random.choice(COLUMNS)
        created_at = _random_date(two_years_ago, now)
        signed_at = None
        if status in ("signed", "published"):
            # 签发时间在创建后 1-7 天内
            signed_at = _random_date(
                created_at,
                min(created_at + timedelta(days=7), now),
            ).strftime("%Y-%m-%d %H:%M:%S")
        rows.append((
            article_id,
            status,
            signed_at,
            created_at.strftime("%Y-%m-%d %H:%M:%S"),
            art_type,
            is_deleted,
            dept,
            author,
            column,
        ))

    cur.executemany(
        "INSERT INTO fact_article_workflow VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    logger.info("Database initialized with %d rows.", len(rows))


async def execute_query(sql: str, db_path: str = DB_PATH) -> dict:
    """异步执行查询，返回 {data: list[dict], columns: list, error: str|None}"""
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description or []]
                data = [dict(row) for row in rows]
        return {"data": data, "columns": columns, "error": None}
    except Exception as e:
        logger.error("execute_query error: %s | SQL: %s", e, sql)
        return {"data": [], "columns": [], "error": str(e)}
