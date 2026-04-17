# handlers/states.py

import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.keyboards import get_citation_format_keyboard, get_main_menu_keyboard, get_year_filter_keyboard, get_sort_filter_keyboard
from core.constants import *
from core.database import is_vip, get_user_usage_today, log_usage, increment_citation_count
from services.research import (
    download_pdf_via_telegram,
    download_direct_pdf,
    search_article_by_doi, 
    search_article_by_name,
    get_article_data_for_citation
)
from services.ai_abstract import get_abstract_from_openalex, analyze_abstract_with_ai


async def show_article_results(update: Update, chat_id: str, articles: list, query: str = None, page: int = 1, min_year: int = None, sort_by: str = "relevance"):
    text_res = f"✅ نتایج یافت شده (صفحه $ {page} $):\n\n"
    keyboard = []
    
    for i, art in enumerate(articles):
        oa_status = "🔓 فایل رایگان موجود" if art.get('oa_url') else "🔒 نیاز به سای‌هاب"
        text_res += f"{i+1}. {art.get('title')} ({art.get('year')})\n👤 {art.get('authors')}\n🔗 DOI: {art.get('doi')}\n📈 استنادات: $ {art.get('citations')} $ | {oa_status}\n\n"
        keyboard.append([KeyboardButton(f"📥 دانلود مقاله {i+1}")])
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(KeyboardButton(BTN_PREV_PAGE))
    if len(articles) == 5: 
        nav_buttons.append(KeyboardButton(BTN_NEXT_PAGE))
        
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    keyboard.append([KeyboardButton(BTN_BACK)])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # ذخیره تمام متغیرها برای صفحات بعد (از جمله نوع مرتب‌سازی)
    set_state(chat_id, 'waiting_article_selection', articles=articles, query=query, page=page, min_year=min_year, sort_by=sort_by)
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
        return
    
    # ====== 1. پردازش دریافت DOI ======
    if step == 'waiting_article_doi':
        await update.message.reply_text("⏳ در حال بررسی شناسه DOI...")
        articles = search_article_by_doi(text)
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای یافت نشد.")
            return
        await show_article_results(update, chat_id, articles)
        return

    # ====== 2. پردازش دریافت نام مقاله و پرسش سال ======
    if step == 'waiting_article_name':
        set_state(chat_id, 'waiting_article_year', query=text)
        await update.message.reply_text(
            "📅 آیا می‌خواهید جستجو محدود به سال خاصی باشد؟", 
            reply_markup=get_year_filter_keyboard()
        )
        return

    # ====== 3. دریافت سال و پرسش درباره مرتب‌سازی ======
    if step == 'waiting_article_year':
        query = state_data.get('query')
        min_year = None
        
        if text == BTN_YEAR_2024: min_year = 2024
        elif text == BTN_YEAR_2020: min_year = 2020
        elif text == BTN_YEAR_2015: min_year = 2015

        # رفتن به مرحله انتخاب نحوه مرتب‌سازی به جای جستجوی مستقیم
        set_state(chat_id, 'waiting_article_sort', query=query, min_year=min_year)
        await update.message.reply_text(
            "🗂 نحوه نمایش نتایج را انتخاب کنید:\n\n"
            "🎯 **مرتبط‌ترین:** مقالاتی که اسمشان دقیقاً مشابه متن شماست.\n"
            "📈 **بیشترین استناد:** مقالات معروف‌تر و پایه در این حوزه.",
            reply_markup=get_sort_filter_keyboard(),
            parse_mode='Markdown'
        )
        return

    # ====== 3.5. پردازش نوع مرتب‌سازی و انجام جستجو ======
    if step == 'waiting_article_sort':
        query = state_data.get('query')
        min_year = state_data.get('min_year')
        
        sort_by = "relevance"
        if text == BTN_SORT_CITATION:
            sort_by = "citation"

        await update.message.reply_text("⏳ در حال جستجوی مقالات...")
        articles = search_article_by_name(query, page=1, min_year=min_year, sort_by=sort_by)
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای یافت نشد.", reply_markup=get_main_menu_keyboard())
            return
        await show_article_results(update, chat_id, articles, query=query, page=1, min_year=min_year, sort_by=sort_by)
        return

    # ====== 4. پردازش انتخاب مقاله یا تغییر صفحه ======
    if step == 'waiting_article_selection':
        query = state_data.get('query')
        page = state_data.get('page', 1)
        min_year = state_data.get('min_year')
        sort_by = state_data.get('sort_by', 'relevance') # دریافت نوع مرتب‌سازی از state
        
        # مدیریت دکمه‌های صفحه بعد و قبل
        if text == BTN_NEXT_PAGE:
            page += 1
            await update.message.reply_text(f"⏳ در حال دریافت صفحه $ {page} $...")
            articles = search_article_by_name(query, page=page, min_year=min_year, sort_by=sort_by)
            if not articles:
                await update.message.reply_text("❌ نتیجه دیگری یافت نشد.")
                return
            await show_article_results(update, chat_id, articles, query, page, min_year, sort_by)
            return
            
        elif text == BTN_PREV_PAGE:
            if page > 1:
                page -= 1
                await update.message.reply_text(f"⏳ در حال دریافت صفحه $ {page} $...")
                articles = search_article_by_name(query, page=page, min_year=min_year, sort_by=sort_by)
                await show_article_results(update, chat_id, articles, query, page, min_year, sort_by)
            return

        # مدیریت دانلود
        if text.startswith("📥 دانلود مقاله "):
            try:
                user_is_vip = is_vip(chat_id)
                daily_limit = 20 if user_is_vip else 2
                usage_today = get_user_usage_today(chat_id, "download_article")
                
                if usage_today >= daily_limit:
                    await update.message.reply_text(f"❌ شما به سقف مجاز دانلود روزانه خود ($ {daily_limit} $ مقاله) رسیده‌اید.")
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
                if oa_url:
                    file_path = await download_direct_pdf(oa_url, doi if (doi and doi != 'ندارد') else f"article_{index}")
                
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
                    await update.message.reply_text("❌ متأسفانه فایل PDF این مقاله یافت نشد.")
            except ValueError:
                 await update.message.reply_text("❌ فرمت دستور اشتباه است.")
        return

    # ====== 5. تولید رفرنس ======
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


 # ====== 6. تحلیل چکیده هوشمند ======
    if step == 'waiting_smart_abstract_doi':
        doi_input = text.strip()
        await update.message.reply_text("⏳ در حال دریافت چکیده مقاله...")
        
        abstract_text = get_abstract_from_openalex(doi_input)
        if not abstract_text:
            await update.message.reply_text("❌ متاسفانه چکیده‌ای برای این مقاله در پایگاه داده یافت نشد.", reply_markup=get_main_menu_keyboard())
            set_state(chat_id, None)
            return
            
        await update.message.reply_text("🧠 چکیده با موفقیت دریافت شد. در حال ارسال به هوش مصنوعی برای تحلیل...\n(این مرحله ممکن است ۱ تا ۲ دقیقه طول بکشد، لطفاً صبور باشید)")
        
        analysis_result = await analyze_abstract_with_ai(abstract_text)
        
        # ثبت یک بار استفاده برای محدودیت روزانه
        log_usage(chat_id, "smart_abstract")
        
        await update.message.reply_text(
            f"📊 **تحلیل چکیده هوشمند:**\n\n{analysis_result}", 
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
        set_state(chat_id, None)
        return
    
    if not step:
        await update.message.reply_text("لطفاً از منوی اصلی استفاده کنید.")
