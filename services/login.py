import asyncio
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv() 
API_ID = os.getenv("API_ID")
API_HASH =  os.getenv("eb06d4abfb49dc3eeb1aeb98ae0f581e")
SESSION_NAME =  os.getenv("my_bale_bot_session")

async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    # اینجا از شما شماره موبایل (با 98+) و سپس کد تایید پیامک شده را می‌پرسد
    await client.start()
    print("✅ با موفقیت لاگین شدید! فایل سشن ساخته شد. حالا می‌توانید ربات اصلی را استارت بزنید.")
    await client.disconnect()

asyncio.run(main())
