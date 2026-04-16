import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.constants import *
from core.database import is_vip, get_user_usage_today, log_usage 
from services.research import (
    download_pdf_via_telegram, 
    search_article_by_doi, 
    search_article_by_name
)

async def show_article_results(update: Update, chat_id: str, articles: list):
    """تابع کمکی برای نمایش نتایج جستجو و ساخت دکمه‌های دانلود"""
    text_res = "✅ نتایج یافت شده:\n\n"
    keyboard = []
    for i, art in enumerate(articles):
        text_res += f"{i+1}. {art.get('title')} ({art.get('year')})\n👤 {art.get('authors')}\n🔗 DOI: {art.get('doi')}\n\n"
        # اضافه کردن دکمه دانلود برای هر مقاله
        keyboard.append([KeyboardButton(f"📥 دانلود مقاله {i+1}")])
    
    keyboard.append([KeyboardButton(BTN_BACK)])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # تغییر وضعیت به حالت انتخاب مقاله و ذخیره لیست مقالات در state
    set_state(chat_id, 'waiting_article_selection', articles=articles)
    await update.message.reply_text(text_res, reply_markup=reply_markup)


async def process_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    state_data = get_state(chat_id)
    step = state_data.get('step')

    if text in ['0', 'لغو', 'شروع', 'بازگشت', BTN_BACK]:
        from .commands import cmd_start
        await cmd_start(update, context)
        return

    # ====== 1. پردازش دریافت DOI ======
    if step == 'waiting_article_doi':
        await update.message.reply_text("⏳ در حال بررسی شناسه DOI...")
        articles = search_article_by_doi(text)
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای با این شناسه در دیتابیس CrossRef یافت نشد.")
            return
        await show_article_results(update, chat_id, articles)
        return

    # ====== 2. پردازش دریافت نام مقاله ======
    if step == 'waiting_article_name':
        await update.message.reply_text("⏳ در حال جستجوی مقالات...")
        articles = search_article_by_name(text, limit=5) # محدود به 5 نتیجه
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای با این کلمات کلیدی یافت نشد.")
            return
        await show_article_results(update, chat_id, articles)
        return

    # ====== 3. پردازش انتخاب و دانلود مقاله ======
    if step == 'waiting_article_selection':
        if text.startswith("📥 دانلود مقاله "):
            try:
                # بررسی محدودیت دانلود روزانه
                user_is_vip = is_vip(chat_id)
                daily_limit = 20 if user_is_vip else 2
                usage_today = get_user_usage_today(chat_id, "download_article")
                
                if usage_today >= daily_limit:
                    await update.message.reply_text(
                        f"❌ شما به سقف مجاز دانلود روزانه خود ($ {daily_limit} $ مقاله) رسیده‌اید.\n"
                        "لطفاً فردا مجدداً تلاش کنید."
                    )
                    return

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
                    
                await update.message.reply_text(f"⏳ در صف دریافت فایل...\nلطفاً تا حدود 10 ثانیه منتظر بمانید.")
                
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
