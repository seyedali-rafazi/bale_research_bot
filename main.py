# main.py

import logging
import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from core.database import init_db
from core.http_client import close_http_session
from core.redis_client import close_redis, init_redis
from core.telethon_client import close_telethon_client
from handlers import register_all_handlers

load_dotenv()
BALE_TOKEN = os.getenv("BALE_TOKEN")
if not BALE_TOKEN:
    raise RuntimeError("BALE_TOKEN must be set in .env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


async def initialize_services(_application):
    await init_db()
    await init_redis()


async def shutdown_services(_application):
    await close_telethon_client()
    await close_http_session()
    await close_redis()


def main():
    application = (
        ApplicationBuilder()
        .token(BALE_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .base_file_url("https://tapi.bale.ai/file/bot")
        .concurrent_updates(True)
        .post_init(initialize_services)
        .post_shutdown(shutdown_services)
        .build()
    )

    register_all_handlers(application)

    print("✅ ربات با معماری async و پشتیبانی همزمان راه‌اندازی شد...")
    application.run_polling()


if __name__ == "__main__":
    main()
