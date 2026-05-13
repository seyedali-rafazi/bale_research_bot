# main.py

import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from core.database import init_db
from core.redis_client import init_redis
from handlers import register_all_handlers

load_dotenv()
BALE_TOKEN = os.getenv("BALE_TOKEN")
if not BALE_TOKEN:
    raise RuntimeError("BALE_TOKEN must be set in .env")

# تنظیمات لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


async def initialize_services(application):
    await init_db()
    await init_redis()


def main():
    application = (
        ApplicationBuilder()
        .token(BALE_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .base_file_url("https://tapi.bale.ai/file/bot")
        .post_init(initialize_services)
        .build()
    )

    register_all_handlers(application)

    print("✅ ربات با معماری جدید با موفقیت راه‌اندازی شد...")
    application.run_polling()


if __name__ == "__main__":
    main()
