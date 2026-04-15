import os
import re
import requests
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

# ==========================================
# تنظیمات Telethon برای دانلود از تلگرام اصلی
# ==========================================

load_dotenv() 
API_ID = os.getenv("API_ID")
API_HASH =  os.getenv("API_HASH")
SESSION_NAME =  os.getenv("my_bale_bot_session")

# ==========================================
# بخش اول: جستجوی مقالات (Crossref)
# ==========================================

def format_crossref_item(item):
    """فرمت کردن دیتای خام کراس‌رف به شکل قابل خواندن برای ربات"""
    title = item.get('title', ['بدون عنوان'])[0]
    
    authors_raw = item.get('author', [])
    authors_list = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_raw]
    authors = ", ".join(filter(None, authors_list))
    if not authors:
        authors = "نامشخص"
        
    return {
        'title': title,
        'authors': authors,
        'publisher': item.get('publisher', 'نامشخص'),
        'doi': item.get('DOI', 'ندارد'),
        'url': item.get('URL', 'ندارد')
    }

def clean_doi(doi_input):
    if not doi_input: return ""
    doi = doi_input.strip()
    return re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi)

def search_article_by_name(query):
    try:
        url = f"https://api.crossref.org/works?query.title={query}&select=DOI,title,author,publisher,URL&rows=5"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            items = res.json().get('message', {}).get('items', [])
            return [format_crossref_item(item) for item in items]
    except Exception as e:
        print(f"Crossref Name Search Error: {e}")
    return []

def search_article_by_doi(doi):
    doi_clean = clean_doi(doi)
    try:
        url = f"https://api.crossref.org/works/{doi_clean}"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            item = res.json().get('message', {})
            if item:
                return [format_crossref_item(item)]
    except Exception as e:
        print(f"Crossref DOI Search Error: {e}")
    return []

# ==========================================
# بخش دوم: دانلود مقاله با استفاده از Telethon
# ==========================================

async def download_pdf_via_telegram(doi_input: str) -> str:
    """دی‌او‌آی را به ربات تلگرام می‌فرستد و فایل دانلود شده را برمی‌گرداند"""
    doi = clean_doi(doi_input)
    if not doi:
        return None

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    # اطمینان از لاگین بودن اکانت تلگرام
    if not await client.is_user_authorized():
        print("⚠️ خطا: اکانت تلگرام لاگین نیست. ابتدا باید یک بار اسکریپت لاگین را اجرا کنید.")
        await client.disconnect()
        return None

    downloaded_file_path = None
    try:
        await client.send_message(SCIHUB_BOT_USERNAME, doi)
        
        # صبر کردن برای پاسخ ربات سای هاب
        await asyncio.sleep(7) 
        
        messages = await client.get_messages(SCIHUB_BOT_USERNAME, limit=3)
        for msg in messages:
            if msg.file and msg.file.ext == '.pdf':
                os.makedirs("downloads", exist_ok=True)
                # نام فایل را ایمن می‌کنیم تا مشکلی در ویندوز/لینوکس پیش نیاید
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
