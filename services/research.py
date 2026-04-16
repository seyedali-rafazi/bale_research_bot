# services/research.py

import os
import re
import requests
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv() 
API_ID = os.getenv("API_ID")
API_HASH =  os.getenv("API_HASH")
SESSION_NAME =  os.getenv("SESSION_NAME")
SCIHUB_BOT_USERNAME = os.getenv("SCIHUB_BOT_USERNAME")

# ایجاد یک قفل سراسری برای جلوگیری از تداخل درخواست‌های همزمان
download_lock = asyncio.Lock()

# ... (توابع format_crossref_item, clean_doi, search_article_by_name, search_article_by_doi را دقیقاً مانند قبل اینجا بگذارید) ...

async def download_pdf_via_telegram(doi_input: str) -> str:
    """دی‌او‌آی را به ربات تلگرام می‌فرستد و فایل دانلود شده را برمی‌گرداند"""
    doi = clean_doi(doi_input)
    if not doi:
        return None

    # با استفاده از قفل مطمئن می‌شویم که در هر لحظه فقط یک درخواست به ربات مرجع ارسال می‌شود
    async with download_lock:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("⚠️ خطا: اکانت تلگرام لاگین نیست. ابتدا باید یک بار اسکریپت لاگین را اجرا کنید.")
            await client.disconnect()
            return None

        downloaded_file_path = None
        try:
            # پاک کردن تاریخچه چت ربات مرجع برای جلوگیری از دریافت فایل‌های قبلی
            # این کار باعث می‌شود همیشه فقط پیام جدید خوانده شود
            await client.delete_dialog(SCIHUB_BOT_USERNAME)
            
            await client.send_message(SCIHUB_BOT_USERNAME, doi)
            
            # صبر کردن برای پاسخ ربات سای هاب
            await asyncio.sleep(8) 
            
            messages = await client.get_messages(SCIHUB_BOT_USERNAME, limit=3)
            for msg in messages:
                if msg.file and msg.file.ext == '.pdf':
                    os.makedirs("downloads", exist_ok=True)
                    safe_name = doi.replace('/', '_').replace('\\', '_')
                    file_path = f"downloads/{safe_name}.pdf"
                    
                    await client.download_media(message=msg, file=file_path)
                    downloaded_file_path = file_path
                    break
        except Exception as e:
            print(f"Error in Telegram fetch: {e}")
        finally:
            await client.disconnect()

        return downloaded_file_path
