# handlers/states.py

import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.constants import *
from core.database import is_vip, get_user_usage_today, log_usage # اضافه شدن دیتابیس
from services.research import  download_pdf_via_telegram

async def process_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    state_data = get_state(chat_id)
    step = state_data.get('step')

    if text in ['0', 'لغو', 'شروع']:
        from .commands import cmd_start
        await cmd_start(update, context)
        return

    # ... (بخش جستجوی مقالات دست نخورده باقی می‌ماند) ...

    elif step == 'waiting_article_selection':
        if text.startswith("📥 دانلود مقاله "):
            try:
                # ====== بررسی محدودیت دانلود روزانه ======
                user_is_vip = is_vip(chat_id)
                daily_limit = 20 if user_is_vip else 2
                usage_today = get_user_usage_today(chat_id, "download_article")
                
                if usage_today >= daily_limit:
                    await update.message.reply_text(
                        f"❌ شما به سقف مجاز دانلود روزانه خود ($ {daily_limit} $ مقاله) رسیده‌اید.\n"
                        "لطفاً فردا مجدداً تلاش کنید."
                    )
                    return
                # =========================================

                index = int(text.replace("📥 دانلود مقاله ", "").strip()) - 1
                articles = state_data.get('articles', [])
                selected_art = articles[index]
                doi = selected_art.get('doi')
                
                if not doi or doi in ['No DOI', 'ندارد']:
                    await update.message.reply_text("❌ این مقاله فاقد شناسه DOI است و قابل دانلود نیست.")
                    return
                    
                await update.message.reply_text(f"⏳ در صف دریافت فایل...\nلطفاً چند ثانیه منتظر بمانید.")
                
                # استفاده از متد جدید Telethon که حالا قفل دارد
                file_path = await download_pdf_via_telegram(doi)
                
                if file_path and os.path.exists(file_path):
                    await update.message.reply_text("✅ فایل دریافت شد. در حال ارسال برای شما...")
                    try:
                        with open(file_path, 'rb') as doc:
                            caption = f"📄 {selected_art['title']}\n🔗 DOI: {doi}"
                            await context.bot.send_document(chat_id=chat_id, document=doc, caption=caption)
                            
                        # ثبت در دیتابیس به عنوان یک دانلود موفق
                        log_usage(chat_id, "download_article")
                        
                    finally:
                        if os.path.exists(file_path): 
                            os.remove(file_path) 
                else:
                    await update.message.reply_text("❌ متأسفانه ربات مرجع نتوانست فایل PDF این مقاله را پیدا کند.")
            except Exception as e:
                print(f"Error in download state: {e}")
                await update.message.reply_text("❌ انتخاب نامعتبر است یا خطایی رخ داد.")
        return
        
    if not step:
        await update.message.reply_text("لطفاً از منو استفاده کنید.")
