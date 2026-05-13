import os
from datetime import datetime, timezone
from typing import Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://bale_bot:secret@localhost:5432/bale_bot",
)
DB_MIN_POOL = int(os.getenv("DB_MIN_POOL", 2))
DB_MAX_POOL = int(os.getenv("DB_MAX_POOL", 20))

db_pool: Optional[asyncpg.pool.Pool] = None


async def get_db_pool() -> asyncpg.pool.Pool:
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=DB_MIN_POOL,
            max_size=DB_MAX_POOL,
        )
    return db_pool


async def init_db():
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                is_vip BOOLEAN DEFAULT FALSE,
                join_date DATE,
                vip_expire_date TIMESTAMPTZ,
                citation_count INTEGER DEFAULT 0,
                book_download_count INTEGER DEFAULT 0
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_stats (
                user_id TEXT,
                action TEXT,
                date DATE,
                count BIGINT DEFAULT 1,
                PRIMARY KEY (user_id, action, date)
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                amount BIGINT,
                payload TEXT,
                provider_charge_id TEXT,
                date TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_usage_stats_user_action_date
            ON usage_stats (user_id, action, date)
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_users_vip_expire_date
            ON users (vip_expire_date)
            """
        )


async def add_transaction(user_id, amount, payload, provider_charge_id):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO transactions (user_id, amount, payload, provider_charge_id) VALUES ($1, $2, $3, $4)",
            str(user_id),
            amount,
            payload,
            provider_charge_id,
        )


async def add_user(user_id, username=None):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO users (user_id, username, join_date) VALUES ($1, $2, CURRENT_DATE) ON CONFLICT(user_id) DO NOTHING",
            str(user_id),
            username,
        )


async def is_vip(user_id):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_vip, vip_expire_date FROM users WHERE user_id = $1",
            str(user_id),
        )
        if not row:
            return False

        if row["is_vip"]:
            expire_date = row["vip_expire_date"]
            if expire_date and datetime.now(timezone.utc) > expire_date:
                await conn.execute(
                    "UPDATE users SET is_vip = FALSE, vip_expire_date = NULL WHERE user_id = $1",
                    str(user_id),
                )
                return False
            return True

        return False


async def set_vip(user_id, status: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_vip = $1 WHERE user_id = $2",
            bool(status),
            str(user_id),
        )
        if status == 0:
            await conn.execute(
                "UPDATE users SET vip_expire_date = NULL WHERE user_id = $1",
                str(user_id),
            )


async def set_vip_with_expiration(user_id, status: int, expire_date: datetime):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        expiration = expire_date.astimezone(timezone.utc) if expire_date else None
        await conn.execute(
            "UPDATE users SET is_vip = $1, vip_expire_date = $2 WHERE user_id = $3",
            bool(status),
            expiration,
            str(user_id),
        )


async def log_usage(user_id, action):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        today = datetime.now(timezone.utc).date()
        await conn.execute(
            """
            INSERT INTO usage_stats (user_id, action, date, count)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (user_id, action, date)
            DO UPDATE SET count = usage_stats.count + 1
            """,
            str(user_id),
            action,
            today,
        )


async def get_total_users():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS total FROM users")
        return row["total"] if row else 0


async def get_user_usage_today(user_id, action):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT count FROM usage_stats WHERE user_id = $1 AND action = $2 AND date = CURRENT_DATE",
            str(user_id),
            action,
        )
        return row["count"] if row else 0


async def get_total_vip_users():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS total FROM users WHERE is_vip = TRUE AND (vip_expire_date IS NULL OR vip_expire_date > NOW())"
        )
        return row["total"] if row else 0


async def get_user_total_usage(user_id):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(SUM(count), 0) AS total FROM usage_stats WHERE user_id = $1",
            str(user_id),
        )
        return row["total"] if row else 0


async def get_citation_count(user_id: str) -> int:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT citation_count FROM users WHERE user_id = $1",
            str(user_id),
        )
        return row["citation_count"] if row and row["citation_count"] is not None else 0


async def increment_citation_count(user_id: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET citation_count = citation_count + 1 WHERE user_id = $1",
            str(user_id),
        )


async def get_book_download_count(user_id: str) -> int:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT book_download_count FROM users WHERE user_id = $1",
            str(user_id),
        )
        return row["book_download_count"] if row and row["book_download_count"] is not None else 0


async def increment_book_download_count(user_id: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET book_download_count = book_download_count + 1 WHERE user_id = $1",
            str(user_id),
        )
