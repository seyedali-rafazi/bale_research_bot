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
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi).strip()
    return doi

def format_crossref_item(item) -> dict:
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

# --- تابع جدید برای استخراج اطلاعات دقیق جهت تولید رفرنس ---
def get_article_data_for_citation(doi_input: str) -> dict:
    doi_clean = clean_doi(doi_input)
    url = f"https://api.crossref.org/works/{doi_clean}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            item = response.json().get('message', {})
            title = item.get('title', [''])[0]
            
            year = ''
            try:
                published = item.get('published-print', item.get('published-online', {}))
                year = published.get('date-parts', [['']])[0][0]
            except Exception:
                year = 'N.d.'
                
            authors_list = item.get('author', [])
            authors = [f"{a.get('family', '')}, {a.get('given', '')}" for a in authors_list]
            
            return {
                'title': title,
                'year': str(year),
                'authors_list': authors, 
                'doi': doi_clean,
                'journal': item.get('container-title', [''])[0]
            }
    except Exception as e:
        print(f"Error fetching exact DOI for citation: {e}")
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
            print("⚠️ خطا: اکانت تلگرام لاگین نیست. ابتدا اسکریپت لاگین را اجرا کنید.")
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
