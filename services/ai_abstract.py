#services/ai_abstract.py

import os
import requests
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
from .research import clean_doi

load_dotenv() 
CHATGPT_BOT_USERNAME = os.getenv("CHATGPT_BOT_USERNAME")
API_ID = os.getenv("API_ID")
API_HASH =  os.getenv("API_HASH")
SESSION_NAME =  os.getenv("SESSION_NAME")

download_lock = None


def get_abstract_from_openalex(doi_input: str) -> str:
    """استخراج چکیده مقاله از openalex"""
    doi_clean = clean_doi(doi_input)
    url = f"https://api.openalex.org/works/https://doi.org/{doi_clean}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            item = response.json()
            idx = item.get('abstract_inverted_index', {})
            if not idx:
                return None
            # بازسازی متن چکیده از ایندکس‌های معکوس
            words = []
            for word, positions in idx.items():
                for pos in positions:
                    words.append((pos, word))
            words.sort(key=lambda x: x[0])
            return " ".join([w[1] for w in words])
    except Exception as e:
        print(f"Error fetching abstract: {e}")
    return None

async def analyze_abstract_with_ai(abstract_text: str) -> str:
    """ارسال چکیده به ربات هوش مصنوعی تلگرام و دریافت پاسخ (با چشم پوشی از استیکر)"""
    global download_lock
    if download_lock is None:
        download_lock = asyncio.Lock()

    async with download_lock:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await client.disconnect()
            return "⚠️ خطا: اکانت تلگرام سرور لاگین نیست."

        try:
            prompt = f"لطفا این چکیده علمی را به طور کامل تحلیل کن و نکات کلیدی آن را بگو:\n\n{abstract_text}"
            await client.send_message(CHATGPT_BOT_USERNAME, prompt)
            
            # منتظر ماندن برای دریافت پاسخ نهایی
            for _ in range(15): # حداکثر 15 بار چک میکند (حدود یک دقیقه و نیم)
                await asyncio.sleep(6) 
                messages = await client.get_messages(CHATGPT_BOT_USERNAME, limit=2)
                
                if not messages:
                    continue
                    
                latest_msg = messages[0]
                
                # اگر پیام متنی بود و متعلق به خودمان (out) نبود و استیکر نبود
                if latest_msg.text and not latest_msg.out and not latest_msg.sticker:
                    return latest_msg.text
                    
            return "❌ زمان انتظار برای تحلیل پایان یافت."
        except Exception as e:
            print(f"Error in AI abstract analysis: {e}")
            return "❌ خطا در برقراری ارتباط با هوش مصنوعی."
        finally:
            await client.disconnect()