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

download_lock = None

def clean_doi(doi: str) -> str:
    if not doi: return ""
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi).strip()
    return doi

def format_openalex_item(item) -> dict:
    title = item.get('title', 'بدون عنوان')
    if not title: title = 'بدون عنوان'
        
    authors_list = item.get('authorships', [])
    author_names = ", ".join([a.get('author', {}).get('display_name', '') for a in authors_list[:3]])
    if len(authors_list) > 3: author_names += " و همکاران"
    
    doi = item.get('doi', 'ندارد')
    if doi and doi != 'ندارد':
        doi = clean_doi(doi)
        
    year = item.get('publication_year', 'نامشخص')
    citations = item.get('cited_by_count', 0)
    
    # بررسی لینک رایگان (Open Access)
    oa_url = item.get('open_access', {}).get('oa_url', None)

    return {
        "title": title,
        "authors": author_names if author_names else "نامشخص",
        "doi": doi,
        "year": str(year),
        "citations": citations,
        "oa_url": oa_url
    }

def search_article_by_name(query, page=1, min_year=None, sort_by="relevance"):
    """
    جستجوی مقاله با قابلیت مرتب‌سازی بر اساس ارتباط یا تعداد استناد
    """
    url = "https://api.openalex.org/works"
    
    params = {
        "search": query,
        "per-page": 5,  
        "page": page
    }
    
    # اگر کاربر مرتب‌سازی بر اساس استناد را انتخاب کرده باشد
    if sort_by == "citation":
        params["sort"] = "cited_by_count:desc"
        
    if min_year:
        params["filter"] = f"from_publication_date:{min_year}-01-01"

    headers = {
        "User-Agent": "BaleBot/1.0"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("results", []):
            formatted_item = format_openalex_item(item)
            if formatted_item:
                results.append(formatted_item)
                
        return results
    except Exception as e:
        print(f"Error searching OpenAlex: {e}")
        return []

def search_article_by_doi(doi_input: str) -> list:
    doi_clean = clean_doi(doi_input)
    url = f"https://api.openalex.org/works/https://doi.org/{doi_clean}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            item = response.json()
            return [format_openalex_item(item)]
    except Exception as e:
        print(f"Error fetching DOI from OpenAlex: {e}")
    return []

def get_article_data_for_citation(doi_input: str) -> dict:
    doi_clean = clean_doi(doi_input)
    url = f"https://api.openalex.org/works/https://doi.org/{doi_clean}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            item = response.json()
            title = item.get('title', '')
            year = item.get('publication_year', 'N.d.')
            
            authors_list = item.get('authorships', [])
            authors = [a.get('author', {}).get('display_name', '') for a in authors_list]
            
            journal = ''
            if item.get('primary_location') and item['primary_location'].get('source'):
                journal = item['primary_location']['source'].get('display_name', '')

            return {
                'title': title,
                'year': str(year),
                'authors_list': authors, 
                'doi': doi_clean,
                'journal': journal
            }
    except Exception as e:
        print(f"Error fetching exact DOI for citation: {e}")
    return None

async def download_direct_pdf(url: str, doi_or_name: str) -> str:
    """دانلود مستقیم فایل از لینک Open Access با بررسی نوع فایل"""
    try:
        os.makedirs("downloads", exist_ok=True)
        safe_name = doi_or_name.replace('/', '_').replace('\\', '_')
        file_path = f"downloads/{safe_name}_direct.pdf"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # برای هندل کردن ریدایرکت‌ها allow_redirects=True به صورت پیشفرض فعال است
        response = requests.get(url, headers=headers, timeout=15, stream=True)
        
        # بررسی اینکه آیا محتوای دریافتی واقعاً PDF است یا خیر
        content_type = response.headers.get('Content-Type', '').lower()
        
        if response.status_code == 200 and 'application/pdf' in content_type:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    if chunk:
                        f.write(chunk)
            
            # بررسی حجم فایل جهت اطمینان (فایل‌های کمتر از 10 کیلوبایت معمولاً خرابند)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 10240: # بزرگتر از $ 10 $ کیلوبایت
                return file_path
            else:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return None
        else:
            print(f"لینک مستقیم PDF نبود. Content-Type دریافتی: {content_type}")
            return None
            
    except Exception as e:
        print(f"Error downloading direct PDF: {e}")
    return None

async def download_pdf_via_telegram(doi_input: str) -> str:
    global download_lock
    if download_lock is None:
        download_lock = asyncio.Lock()

    doi = clean_doi(doi_input)
    if not doi:
        return None

    async with download_lock:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("⚠️ خطا: اکانت تلگرام لاگین نیست.")
            await client.disconnect()
            return None

        downloaded_file_path = None
        try:
            await client.delete_dialog(SCIHUB_BOT_USERNAME)
            await client.send_message(SCIHUB_BOT_USERNAME, doi)
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
