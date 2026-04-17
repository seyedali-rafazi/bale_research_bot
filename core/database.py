# core/database.py

import sqlite3
from datetime import datetime

DB_NAME = "bot_data.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # جدول کاربران
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            is_vip INTEGER DEFAULT 0,
            join_date TEXT,
            vip_expire_date TEXT,
            citation_count INTEGER DEFAULT 0
        )
    """)

    # اضافه کردن امن ستون‌ها در صورت عدم وجود (بدون پاک شدن دیتابیس)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN vip_expire_date TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN citation_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN book_download_count INTEGER DEFAULT 0"
        )
    except sqlite3.OperationalError:
        pass

    # جدول آمار استفاده
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_stats (
            user_id TEXT,
            action TEXT,
            date TEXT,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, action, date)
        )
    """)

    # جدول تراکنش‌ها
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            amount INTEGER,
            payload TEXT,
            provider_charge_id TEXT,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_transaction(user_id, amount, payload, provider_charge_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO transactions (user_id, amount, payload, provider_charge_id, date)
        VALUES (?, ?, ?, ?, ?)
    """,
        (str(user_id), amount, payload, provider_charge_id, current_time),
    )
    conn.commit()
    conn.close()


def add_user(user_id, username=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, join_date) VALUES (?, ?, ?)",
        (user_id, username, today),
    )
    conn.commit()
    conn.close()


def is_vip(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT is_vip, vip_expire_date FROM users WHERE user_id = ?", (user_id,)
    )
    result = cursor.fetchone()

    if not result:
        conn.close()
        return False

    vip_status, expire_date_str = result

    if vip_status == 1:
        if expire_date_str:
            expire_date = datetime.fromisoformat(expire_date_str)
            if datetime.now() > expire_date:
                cursor.execute(
                    "UPDATE users SET is_vip = 0, vip_expire_date = NULL WHERE user_id = ?",
                    (user_id,),
                )
                conn.commit()
                conn.close()
                return False
        conn.close()
        return True

    conn.close()
    return False


def set_vip(user_id, status: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if status == 0:
        cursor.execute(
            "UPDATE users SET is_vip = ?, vip_expire_date = NULL WHERE user_id = ?",
            (status, user_id),
        )
    else:
        cursor.execute(
            "UPDATE users SET is_vip = ? WHERE user_id = ?", (status, user_id)
        )
    conn.commit()
    conn.close()


def set_vip_with_expiration(user_id, status: int, expire_date: datetime):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    expire_date_str = expire_date.isoformat() if expire_date else None
    cursor.execute(
        "UPDATE users SET is_vip = ?, vip_expire_date = ? WHERE user_id = ?",
        (status, expire_date_str, user_id),
    )
    conn.commit()
    conn.close()


def log_usage(user_id, action):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        INSERT INTO usage_stats (user_id, action, date, count) 
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, action, date) 
        DO UPDATE SET count = count + 1
    """,
        (user_id, action, today),
    )
    conn.commit()
    conn.close()


def get_total_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_user_usage_today(user_id, action):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT count FROM usage_stats WHERE user_id = ? AND action = ? AND date = ?",
        (user_id, action, today),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def get_total_vip_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE is_vip = 1 AND (vip_expire_date IS NULL OR vip_expire_date > ?)",
        (now_str,),
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_user_total_usage(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(count) FROM usage_stats WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else 0


# --- توابع جدید برای رفرنس‌دهی ---
def get_citation_count(user_id: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT citation_count FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def increment_citation_count(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET citation_count = citation_count + 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def get_book_download_count(user_id: str) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT book_download_count FROM users WHERE user_id = ?", (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else 0


def increment_book_download_count(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET book_download_count = book_download_count + 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
