# services/research.py

import os
import re
import requests
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv() 
API_ID = os.getenv("API_ID")
API_HASH =  os.getenv("API_HASH")
SESSION_NAME =  os.getenv("SESSION_NAME")
SCIHUB_BOT_USERNAME = os.getenv("SCIHUB_BOT_USERNAME")

# متغیر قفل، مقداردهی آن در داخل تابع انجام می‌شود تا باعث ارور نشود
download_lock = None

def clean_doi(doi: str) -> str:
    """پاکسازی لینک و استخراج فقط خود شناسه DOI"""
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi).strip()
    return doi

def format_crossref_item(item) -> dict:
    """مرتب‌سازی اطلاعات دریافتی از API مقالات"""
    title = item.get('title', ['بدون عنوان'])[0]
    authors = item.get('author', [])
    author_names = ", ".join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors])
    doi = item.get('DOI', 'ندارد')
    
    year = ''
    try:
        published = item.get('published-print', item.get('published-online', {}))
        year = published.get('date-parts', [['']])[0][0]
    except Exception:
        pass
    
    return {
        "title": title,
        "authors": author_names if author_names else "نامشخص",
        "doi": doi,
        "year": str(year)
    }

def search_article_by_name(query: str, limit: int = 5) -> list:
    """جستجوی مقاله بر اساس نام از طریق API CrossRef"""
    url = f"https://api.crossref.org/works?query={query}&select=title,author,DOI,published-print,published-online&rows={limit}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            items = response.json().get('message', {}).get('items', [])
            return [format_crossref_item(item) for item in items]
    except Exception as e:
        print(f"Error searching CrossRef by name: {e}")
    return []

def search_article_by_doi(doi_input: str) -> list:
    """جستجوی اطلاعات مقاله بر اساس DOI از طریق API CrossRef"""
    doi_clean = clean_doi(doi_input)
    url = f"https://api.crossref.org/works/{doi_clean}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            item = response.json().get('message', {})
            return [format_crossref_item(item)]
    except Exception as e:
        print(f"Error fetching DOI from CrossRef: {e}")
    return []

async def download_pdf_via_telegram(doi_input: str) -> str:
    """ارسال DOI به ربات تلگرام سای‌هاب و دریافت فایل PDF"""
    global download_lock
    if download_lock is None:
        download_lock = asyncio.Lock()

    doi = clean_doi(doi_input)
    if not doi:
        return None

    # استفاده از قفل برای جلوگیری از تداخل کاربران همزمان
    async with download_lock:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("⚠️ خطا: اکانت تلگرام لاگین نیست. ابتدا اسکریپت لاگین را اجرا کنید.")
            await client.disconnect()
            return None

        downloaded_file_path = None
        try:
            # پاک کردن تاریخچه قبلی با ربات مرجع برای جلوگیری از دریافت فایل‌های قدیمی
            await client.delete_dialog(SCIHUB_BOT_USERNAME)
            
            # ارسال شناسه مقاله به ربات مرجع
            await client.send_message(SCIHUB_BOT_USERNAME, doi)
            
            # صبر برای دریافت فایل (۸ ثانیه)
            await asyncio.sleep(8) 
            
            # بررسی ۳ پیام آخر ربات مرجع
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
            # همیشه در پایان اتصال را قطع کن
            await client.disconnect()

        return downloaded_file_path
