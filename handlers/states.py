import os
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.constants import *
# اطمینان حاصل کنید که این 3 تابع حتماً در core/database.py وجود داشته باشند
from core.database import is_vip, get_user_usage_today, log_usage 
from services.research import download_pdf_via_telegram

async def process_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    state_data = get_state(chat_id)
    step = state_data.get('step')

    if text in ['0', 'لغو', 'شروع', 'بازگشت']:
        from .commands import cmd_start
        await cmd_start(update, context)
        return

    if step == 'waiting_article_selection':
        if text.startswith("📥 دانلود مقاله "):
            try:
                # ====== بررسی محدودیت دانلود روزانه ======
                # بررسی وضعیت کاربر (VIP یا عادی)
                user_is_vip = is_vip(chat_id)
                daily_limit = 20 if user_is_vip else 2
                
                # دریافت آمار دانلود امروز
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
                
                if index < 0 or index >= len(articles):
                    await update.message.reply_text("❌ انتخاب نامعتبر است.")
                    return
                    
                selected_art = articles[index]
                doi = selected_art.get('doi')
                
                if not doi or doi in ['No DOI', 'ندارد']:
                    await update.message.reply_text("❌ این مقاله فاقد شناسه DOI است و قابل دانلود نیست.")
                    return
                    
                await update.message.reply_text(f"⏳ در صف دریافت فایل...\nلطفاً چند ثانیه منتظر بمانید.")
                
                # دانلود فایل
                file_path = await download_pdf_via_telegram(doi)
                
                if file_path and os.path.exists(file_path):
                    await update.message.reply_text("✅ فایل دریافت شد. در حال ارسال برای شما...")
                    try:
                        with open(file_path, 'rb') as doc:
                            caption = f"📄 {selected_art.get('title', 'مقاله')}\n🔗 DOI: {doi}"
                            await context.bot.send_document(chat_id=chat_id, document=doc, caption=caption)
                            
                        # پس از ارسال موفق، آمار دانلود آپدیت می‌شود
                        log_usage(chat_id, "download_article")
                        
                    finally:
                        if os.path.exists(file_path): 
                            os.remove(file_path) 
                else:
                    await update.message.reply_text("❌ متأسفانه ربات مرجع نتوانست فایل PDF این مقاله را پیدا کند.")
            except ValueError:
                 await update.message.reply_text("❌ فرمت دستور اشتباه است.")
            except Exception as e:
                print(f"Error in download state: {e}")
                await update.message.reply_text("❌ خطایی رخ داد.")
        return
        
    if not step:
        await update.message.reply_text("لطفاً از منوی اصلی استفاده کنید.")
