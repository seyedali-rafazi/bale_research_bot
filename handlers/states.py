# handlers/states.py

import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.constants import *
from services.research import search_article_by_name, search_article_by_doi, get_scihub_pdf_url, download_pdf

async def process_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    state_data = get_state(chat_id)
    step = state_data.get('step')

    if text in ['0', 'لغو', 'شروع']:
        from .commands import cmd_start
        await cmd_start(update, context)
        return

    if step in ['waiting_article_name', 'waiting_article_doi']:
        await update.message.reply_text("⏳ در حال جستجو در پایگاه داده مقالات...")
        
        if step == 'waiting_article_name':
            results = await asyncio.to_thread(search_article_by_name, text)
        else:
            results = await asyncio.to_thread(search_article_by_doi, text)
            
        if not results:
            await update.message.reply_text("❌ متأسفانه مقاله‌ای پیدا نشد.")
            return
            
        res_text = f"🔎 **نتایج جستجو:**\n\n"
        download_buttons = []
        
        for i, art in enumerate(results, 1):
            res_text += (f"{i}️⃣ **{art['title']}**\n"
                         f"👤 نویسندگان: {art['authors']}\n"
                         f"🏢 ناشر: {art['publisher']}\n"
                         f"🔗 DOI: `{art['doi']}`\n")
                         
            # اگر مقاله DOI معتبر داشته باشد، دکمه دانلود را اضافه می‌کنیم
            if art['doi'] != 'No DOI':
                download_buttons.append(KeyboardButton(f"📥 دانلود مقاله {i}"))
            else:
                res_text += "❌ فاقد شناسه DOI برای دانلود.\n"
            
            res_text += "〰️〰️〰️\n"
            
        keyboard = [download_buttons[i:i+2] for i in range(0, len(download_buttons), 2)]
        keyboard.append([KeyboardButton(BTN_BACK)])
        
        set_state(chat_id, 'waiting_article_selection', articles=results)
        await update.message.reply_text(res_text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="Markdown")
        return

    elif step == 'waiting_article_selection':
        if text.startswith("📥 دانلود مقاله "):
            try:
                index = int(text.replace("📥 دانلود مقاله ", "").strip()) - 1
                articles = state_data.get('articles', [])
                selected_art = articles[index]
                doi = selected_art.get('doi')
                
                if not doi or doi == 'No DOI':
                    await update.message.reply_text("❌ این مقاله فاقد شناسه DOI است و قابل دانلود نیست.")
                    return
                    
                await update.message.reply_text(f"⏳ در حال جستجوی فایل PDF در سرورها (دور زدن تحریم)...\nممکن است ۳۰ ثانیه طول بکشد.")
                
                # پیدا کردن لینک دانلود از طریق Sci-Hub
                pdf_url = await asyncio.to_thread(get_scihub_pdf_url, doi)
                
                if not pdf_url:
                    await update.message.reply_text("❌ متأسفانه فایل PDF این مقاله در دیتابیس‌های در دسترس یافت نشد.")
                    return
                    
                await update.message.reply_text("✅ لینک دانلود پیدا شد. در حال دریافت فایل...")
                
                safe_name = f"article_{chat_id}_{index}"
                file_path = await asyncio.to_thread(download_pdf, pdf_url, safe_name)
                
                if file_path and os.path.exists(file_path):
                    await update.message.reply_text("✅ در حال آپلود فایل در تلگرام...")
                    try:
                        with open(file_path, 'rb') as doc:
                            caption = f"📄 {selected_art['title']}\n🔗 DOI: {doi}"
                            await context.bot.send_document(chat_id=chat_id, document=doc, caption=caption)
                    finally:
                        if os.path.exists(file_path): os.remove(file_path) 
                else:
                    await update.message.reply_text("❌ خطا در دانلود فایل PDF.")
            except Exception as e:
                await update.message.reply_text("❌ انتخاب نامعتبر است یا خطایی رخ داد.")
        return
        
    if not step:
        await update.message.reply_text("لطفاً از منو استفاده کنید.")
