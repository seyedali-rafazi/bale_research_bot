# handlers/states.py

import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.keyboards import get_citation_format_keyboard, get_main_menu_keyboard
from core.constants import *
from core.database import is_vip, get_user_usage_today, log_usage, increment_citation_count
from services.research import (
    download_pdf_via_telegram,
    download_direct_pdf,
    search_article_by_doi, 
    search_article_by_name,
    get_article_data_for_citation
)

async def show_article_results(update: Update, chat_id: str, articles: list):
    text_res = "✅ نتایج یافت شده (مرتب شده بر اساس استناد):\n\n"
    keyboard = []
    for i, art in enumerate(articles):
        oa_status = "🔓 فایل رایگان موجود" if art.get('oa_url') else "🔒 نیاز به سای‌هاب"
        text_res += f"{i+1}. {art.get('title')} ({art.get('year')})\n👤 {art.get('authors')}\n🔗 DOI: {art.get('doi')}\n📈 استنادات: $ {art.get('citations')} $ | {oa_status}\n\n"
        keyboard.append([KeyboardButton(f"📥 دانلود مقاله {i+1}")])
    
    keyboard.append([KeyboardButton(BTN_BACK)])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
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

    # ====== پردازش پشتیبانی ======
    if step == 'waiting_support_message':
        admin_id = os.getenv("ADMIN_ID")
        if admin_id:
            msg_to_admin = f"📩 **پیام جدید از پشتیبانی**\n\n👤 آیدی کاربر: `{chat_id}`\n\nمتن پیام:\n{text}"
            await context.bot.send_message(chat_id=admin_id, text=msg_to_admin)
            await update.message.reply_text("✅ پیام شما با موفقیت برای تیم پشتیبانی ارسال شد.")
            from .commands import cmd_start
            await cmd_start(update, context)
        else:
            await update.message.reply_text("❌ خطای سیستمی: آیدی ادمین تنظیم نشده است.")
        return
    
    # ====== 1. پردازش دریافت DOI برای مقالات ======
    if step == 'waiting_article_doi':
        await update.message.reply_text("⏳ در حال بررسی شناسه DOI...")
        articles = search_article_by_doi(text)
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای یافت نشد.")
            return
        await show_article_results(update, chat_id, articles)
        return

    # ====== 2. پردازش دریافت نام مقاله ======
    if step == 'waiting_article_name':
        await update.message.reply_text("⏳ در حال جستجوی مقالات...")
        articles = search_article_by_name(text, limit=5)
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای یافت نشد.")
            return
        await show_article_results(update, chat_id, articles)
        return

    # ====== 3. پردازش انتخاب و دانلود مقاله ======
    if step == 'waiting_article_selection':
        if text.startswith("📥 دانلود مقاله "):
            try:
                user_is_vip = is_vip(chat_id)
                daily_limit = 20 if user_is_vip else 2
                usage_today = get_user_usage_today(chat_id, "download_article")
                
                if usage_today >= daily_limit:
                    await update.message.reply_text(
                        f"❌ شما به سقف مجاز دانلود روزانه خود ($ {daily_limit} $ مقاله) رسیده‌اید."
                    )
                    return

                index = int(text.replace("📥 دانلود مقاله ", "").strip()) - 1
                articles = state_data.get('articles', [])
                
                if index < 0 or index >= len(articles):
                    await update.message.reply_text("❌ انتخاب نامعتبر است.")
                    return
                    
                selected_art = articles[index]
                doi = selected_art.get('doi')
                oa_url = selected_art.get('oa_url')
                
                await update.message.reply_text(f"⏳ در حال دریافت فایل... لطفاً منتظر بمانید.")
                
                file_path = None
                
                # اولویت با لینک رایگان (Open Access)
                if oa_url:
                    file_path = await download_direct_pdf(oa_url, doi if (doi and doi != 'ندارد') else f"article_{index}")
                
                # اگر رایگان نبود یا دانلود مستقیم شکست خورد، از سای‌هاب تلاش می‌کنیم
                if not file_path and doi and doi != 'ندارد':
                    file_path = await download_pdf_via_telegram(doi)
                
                if file_path and os.path.exists(file_path):
                    await update.message.reply_text("✅ فایل دریافت شد. در حال ارسال برای شما...")
                    try:
                        with open(file_path, 'rb') as doc:
                            caption = f"📄 {selected_art.get('title', 'مقاله')}\n🔗 DOI: {doi}"
                            await context.bot.send_document(chat_id=chat_id, document=doc, caption=caption)
                            
                        log_usage(chat_id, "download_article")
                    finally:
                        if os.path.exists(file_path): 
                            os.remove(file_path) 
                else:
                    await update.message.reply_text("❌ متأسفانه فایل PDF این مقاله در منابع باز و سای‌هاب یافت نشد.")
            except ValueError:
                 await update.message.reply_text("❌ فرمت دستور اشتباه است.")
            except Exception as e:
                print(f"Error in download state: {e}")
                await update.message.reply_text("❌ خطایی رخ داد.")
        return

    # ====== 4. پردازش دریافت DOI برای تولید رفرنس ======
    if step == 'waiting_for_citation_doi':
        doi_input = text.strip()
        await update.message.reply_text("⏳ در حال دریافت اطلاعات مقاله...")
        
        article_data = get_article_data_for_citation(doi_input)
        if not article_data:
            await update.message.reply_text("❌ مقاله‌ای با این DOI یافت نشد.")
            return
            
        set_state(chat_id, 'waiting_for_citation_format', article=article_data)
        await update.message.reply_text(
            f"✅ مقاله یافت شد:\n*{article_data['title']}*\n\nلطفاً فرمت رفرنس‌دهی را انتخاب کنید:",
            reply_markup=get_citation_format_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ====== 5. پردازش انتخاب فرمت و ساخت رفرنس ======
    if step == 'waiting_for_citation_format':
        article = state_data.get('article')
        if not article:
            await update.message.reply_text("❌ خطا در بازیابی اطلاعات.")
            set_state(chat_id, None)
            return

        authors = ", ".join(article['authors_list']) if article['authors_list'] else "Unknown Author"
        title = article['title']
        year = article['year']
        journal = article['journal']
        doi = article['doi']
        
        citation_text = ""
        
        if text == BTN_APA:
            citation_text = f"{authors} ({year}). {title}. {journal}. https://doi.org/{doi}"
        elif text == BTN_IEEE:
            citation_text = f"{authors}, \"{title},\" {journal}, {year}. doi: {doi}"
        elif text == BTN_HARVARD:
            citation_text = f"{authors}, {year}. {title}. {journal}. Available at: https://doi.org/{doi}"
        else:
            await update.message.reply_text("❌ لطفاً فرمت را از گزینه‌های پایین انتخاب کنید.")
            return

        increment_citation_count(chat_id)

        await update.message.reply_text(
            f"📑 **رفرنس تولید شده ({text}):**\n\n`{citation_text}`",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
        set_state(chat_id, None) 
        return

    if not step:
        await update.message.reply_text("لطفاً از منوی اصلی استفاده کنید.")
