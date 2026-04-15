"""
初始化本地 SQLite 开发数据库
生成约 1000 条模拟稿件数据，用于本地测试
"""

import asyncio
import random
from datetime import date, timedelta

import aiosqlite

import config

DEPARTMENTS = ["时政部", "经济部", "科技部", "文化部", "体育部", "国际部"]
CATEGORIES = ["新闻", "评论", "深度", "专题", "快讯"]
STATUSES = ["draft", "reviewing", "approved", "published", "rejected"]
STATUS_WEIGHTS = [0.05, 0.05, 0.35, 0.45, 0.10]

AUTHORS = [f"记者{chr(65 + i)}" for i in range(20)]


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        # 建表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                author       TEXT,
                department   TEXT,
                category     TEXT,
                status       TEXT,
                created_at   DATE,
                approved_at  DATE,
                published_at DATE,
                word_count   INTEGER,
                views        INTEGER DEFAULT 0
            )
        """)

        # 清空旧数据
        await db.execute("DELETE FROM articles")

        # 生成模拟数据
        today = date.today()
        start_date = date(today.year - 1, 1, 1)
        rows = []

        for i in range(1, 1001):
            dept = random.choice(DEPARTMENTS)
            author = random.choice(AUTHORS)
            category = random.choice(CATEGORIES)
            status = random.choices(STATUSES, STATUS_WEIGHTS)[0]

            created_at = random_date(start_date, today)
            approved_at = None
            published_at = None

            if status in ("approved", "published"):
                approved_at = created_at + timedelta(days=random.randint(1, 5))
                if approved_at > today:
                    approved_at = today
            if status == "published":
                published_at = approved_at + timedelta(days=random.randint(0, 3))
                if published_at > today:
                    published_at = today

            rows.append((
                f"稿件标题#{i:04d}",
                author,
                dept,
                category,
                status,
                str(created_at),
                str(approved_at) if approved_at else None,
                str(published_at) if published_at else None,
                random.randint(300, 5000),
                random.randint(0, 10000),
            ))

        await db.executemany("""
            INSERT INTO articles
              (title, author, department, category, status,
               created_at, approved_at, published_at, word_count, views)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

        await db.commit()
        count = await db.execute("SELECT COUNT(*) FROM articles")
        row = await count.fetchone()
        print(f"✅ 数据库初始化完成，共插入 {row[0]} 条记录 → {config.DB_PATH}")


if __name__ == "__main__":
    asyncio.run(init_db())
