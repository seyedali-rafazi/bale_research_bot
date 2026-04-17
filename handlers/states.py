# handlers/states.py

import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import get_state, set_state
from core.keyboards import (
    get_citation_format_keyboard,
    get_main_menu_keyboard,
    get_year_filter_keyboard,
    get_sort_filter_keyboard,
    get_books_inline_keyboard,
)
from core.constants import *
from core.database import (
    is_vip,
    get_user_usage_today,
    log_usage,
    increment_citation_count,
)
from services.research import (
    smart_download_pdf,
    search_article_by_doi,
    search_article_by_name,
    get_article_data_for_citation,
)
from services.ai_abstract import get_abstract_from_openalex, analyze_abstract_with_ai
from services.extra_tools import translate_text_with_ai, get_bibtex_from_openalex
from services.book_service import search_books_by_name


async def show_article_results(
    update: Update,
    chat_id: str,
    articles: list,
    query: str = None,
    page: int = 1,
    min_year: int = None,
    sort_by: str = "relevance",
):
    text_res = f"✅ نتایج یافت شده (صفحه $ {page} $):\n\n"
    keyboard = []

    for i, art in enumerate(articles):
        if art.get("is_oa") or art.get("pdf_urls"):
            oa_status = "✅ Available (Open Access)"
        else:
            oa_status = "🤖 Need Sci-Hub"

        text_res += (
            f"<b>{i + 1}. Title:</b> {art.get('title')} ({art.get('year')})\n"
            f"👥 <b>Authors:</b> {art.get('authors')}\n"
            f"🔗 <b>DOI:</b> {art.get('doi')}\n"
            f"📈 <b>Citation:</b> $ {art.get('citations')} $\n"
            f"📄 <b>Access:</b> {oa_status}\n"
            f"────────────────────\n"
        )
        keyboard.append([KeyboardButton(f"📥 دانلود مقاله {i + 1}")])

    nav_buttons = []
    if page > 1:
        nav_buttons.append(KeyboardButton(BTN_PREV_PAGE))
    if len(articles) == 5:
        nav_buttons.append(KeyboardButton(BTN_NEXT_PAGE))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([KeyboardButton(BTN_BACK)])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    set_state(
        chat_id,
        "waiting_article_selection",
        articles=articles,
        query=query,
        page=page,
        min_year=min_year,
        sort_by=sort_by,
    )

    await update.message.reply_text(
        text_res, reply_markup=reply_markup, parse_mode="HTML"
    )


async def process_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    state_data = get_state(chat_id)
    step = state_data.get("step")

    if text in ["0", "لغو", "شروع", "بازگشت", BTN_BACK]:
        from .commands import cmd_start

        await cmd_start(update, context)
        return

    # ====== پردازش پشتیبانی ======
    if step == "waiting_support_message":
        admin_id = os.getenv("ADMIN_ID")
        if admin_id:
            msg_to_admin = f"📩 **پیام جدید از پشتیبانی**\n\n👤 آیدی کاربر: `{chat_id}`\n\nمتن پیام:\n{text}"
            await context.bot.send_message(chat_id=admin_id, text=msg_to_admin)
            await update.message.reply_text(
                "✅ پیام شما با موفقیت برای تیم پشتیبانی ارسال شد."
            )
            from .commands import cmd_start

            await cmd_start(update, context)
        return

    # ====== 1. پردازش دریافت DOI ======
    if step == "waiting_article_doi":
        await update.message.reply_text("⏳ در حال بررسی شناسه DOI...")
        articles = search_article_by_doi(text)
        if not articles:
            await update.message.reply_text("❌ مقاله‌ای یافت نشد.")
            return
        await show_article_results(update, chat_id, articles)
        return

    # ====== 2. پردازش دریافت نام مقاله و پرسش سال ======
    if step == "waiting_article_name":
        set_state(chat_id, "waiting_article_year", query=text)
        await update.message.reply_text(
            "📅 آیا می‌خواهید جستجو محدود به سال خاصی باشد؟",
            reply_markup=get_year_filter_keyboard(),
        )
        return

    # ====== 3. دریافت سال و پرسش درباره مرتب‌سازی ======
    if step == "waiting_article_year":
        query = state_data.get("query")
        min_year = None

        if text == BTN_YEAR_2024:
            min_year = 2024
        elif text == BTN_YEAR_2020:
            min_year = 2020
        elif text == BTN_YEAR_2015:
            min_year = 2015

        set_state(chat_id, "waiting_article_sort", query=query, min_year=min_year)
        await update.message.reply_text(
            "🗂 نحوه نمایش نتایج را انتخاب کنید:\n\n"
            "🎯 **مرتبط‌ترین:** مقالاتی که اسمشان دقیقاً مشابه متن شماست.\n"
            "📈 **بیشترین استناد:** مقالات معروف‌تر و پایه در این حوزه.",
            reply_markup=get_sort_filter_keyboard(),
            parse_mode="Markdown",
        )
        return

    # ====== 3.5. پردازش نوع مرتب‌سازی و انجام جستجو ======
    if step == "waiting_article_sort":
        query = state_data.get("query")
        min_year = state_data.get("min_year")

        sort_by = "relevance"
        if text == BTN_SORT_CITATION:
            sort_by = "citation"

        await update.message.reply_text("⏳ در حال جستجوی مقالات...")
        articles = search_article_by_name(
            query, page=1, min_year=min_year, sort_by=sort_by
        )
        if not articles:
            await update.message.reply_text(
                "❌ مقاله‌ای یافت نشد.", reply_markup=get_main_menu_keyboard()
            )
            return
        await show_article_results(
            update,
            chat_id,
            articles,
            query=query,
            page=1,
            min_year=min_year,
            sort_by=sort_by,
        )
        return

    # ====== 4. پردازش انتخاب مقاله یا تغییر صفحه ======
    if step == "waiting_article_selection":
        query = state_data.get("query")
        page = state_data.get("page", 1)
        min_year = state_data.get("min_year")
        sort_by = state_data.get("sort_by", "relevance")

        if text == BTN_NEXT_PAGE:
            page += 1
            await update.message.reply_text(f"⏳ در حال دریافت صفحه $ {page} $...")
            articles = search_article_by_name(
                query, page=page, min_year=min_year, sort_by=sort_by
            )
            if not articles:
                await update.message.reply_text("❌ نتیجه دیگری یافت نشد.")
                return
            await show_article_results(
                update, chat_id, articles, query, page, min_year, sort_by
            )
            return

        elif text == BTN_PREV_PAGE:
            if page > 1:
                page -= 1
                await update.message.reply_text(f"⏳ در حال دریافت صفحه $ {page} $...")
                articles = search_article_by_name(
                    query, page=page, min_year=min_year, sort_by=sort_by
                )
                await show_article_results(
                    update, chat_id, articles, query, page, min_year, sort_by
                )
            return

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
                articles = state_data.get("articles", [])

                if index < 0 or index >= len(articles):
                    await update.message.reply_text("❌ انتخاب نامعتبر است.")
                    return

                selected_art = articles[index]
                doi = selected_art.get("doi", "ندارد")

                status_msg = await update.message.reply_text(
                    "⏳ در حال پردازش درخواست دانلود..."
                )

                file_path = await smart_download_pdf(selected_art, status_msg)

                if file_path and os.path.exists(file_path):
                    await status_msg.edit_text(
                        "✅ فایل با موفقیت دریافت شد. در حال ارسال برای شما..."
                    )
                    try:
                        with open(file_path, "rb") as doc:
                            caption = f"📄 {selected_art.get('title', 'مقاله')}\n🔗 DOI: {doi}"
                            await context.bot.send_document(
                                chat_id=chat_id, document=doc, caption=caption
                            )
                        log_usage(chat_id, "download_article")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)

            except ValueError:
                await update.message.reply_text("❌ فرمت دستور اشتباه است.")
        return

    # ====== 5. تولید رفرنس ======
    if step == "waiting_for_citation_doi":
        doi_input = text.strip()
        await update.message.reply_text("⏳ در حال دریافت اطلاعات مقاله...")

        article_data = get_article_data_for_citation(doi_input)
        if not article_data:
            await update.message.reply_text("❌ مقاله‌ای با این DOI یافت نشد.")
            return

        set_state(chat_id, "waiting_for_citation_format", article=article_data)
        await update.message.reply_text(
            f"✅ مقاله یافت شد:\n*{article_data['title']}*\n\nلطفاً فرمت رفرنس‌دهی را انتخاب کنید:",
            reply_markup=get_citation_format_keyboard(),
            parse_mode="Markdown",
        )
        return

    if step == "waiting_for_citation_format":
        article = state_data.get("article")
        if not article:
            await update.message.reply_text("❌ خطا در بازیابی اطلاعات.")
            set_state(chat_id, None)
            return

        authors = (
            ", ".join(article["authors_list"])
            if article["authors_list"]
            else "Unknown Author"
        )
        title = article["title"]
        year = article["year"]
        journal = article["journal"]
        doi = article["doi"]

        citation_text = ""

        if text == BTN_APA:
            citation_text = (
                f"{authors} ({year}). {title}. {journal}. https://doi.org/{doi}"
            )
        elif text == BTN_IEEE:
            citation_text = f'{authors}, "{title}," {journal}, {year}. doi: {doi}'
        elif text == BTN_HARVARD:
            citation_text = f"{authors}, {year}. {title}. {journal}. Available at: https://doi.org/{doi}"
        else:
            await update.message.reply_text(
                "❌ لطفاً فرمت را از گزینه‌های پایین انتخاب کنید."
            )
            return

        increment_citation_count(chat_id)

        await update.message.reply_text(
            f"📑 **رفرنس تولید شده ({text}):**\n\n`{citation_text}`",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        set_state(chat_id, None)
        return

    # ====== 6. تحلیل چکیده هوشمند ======
    if step == "waiting_smart_abstract_doi":
        doi_input = text.strip()
        await update.message.reply_text("⏳ در حال دریافت چکیده مقاله...")

        abstract_text = get_abstract_from_openalex(doi_input)
        if not abstract_text:
            await update.message.reply_text(
                "❌ متاسفانه چکیده‌ای برای این مقاله در پایگاه داده یافت نشد.",
                reply_markup=get_main_menu_keyboard(),
            )
            set_state(chat_id, None)
            return

        await update.message.reply_text(
            "🧠 چکیده با موفقیت دریافت شد. در حال ارسال به هوش مصنوعی برای تحلیل...\n(این مرحله ممکن است ۱ تا ۲ دقیقه طول بکشد، لطفاً صبور باشید)"
        )

        analysis_result = await analyze_abstract_with_ai(abstract_text)
        log_usage(chat_id, "smart_abstract")

        await update.message.reply_text(
            f"📊 **تحلیل چکیده هوشمند:**\n\n{analysis_result}",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        set_state(chat_id, None)
        return

    # ====== 7. ترجمه متن دلخواه ======
    if step == "waiting_translate_text":
        english_text = text.strip()
        if len(english_text) < 10:
            await update.message.reply_text(
                "❌ متن وارد شده بسیار کوتاه است. لطفاً یک متن کامل‌تر بفرستید."
            )
            return

        await update.message.reply_text(
            "⏳ در حال ترجمه متن... (این فرآیند ممکن است چند ثانیه زمان ببرد)"
        )

        translated_text = await translate_text_with_ai(english_text)
        log_usage(chat_id, "translate_text")

        await update.message.reply_text(
            f"🇮🇷 **ترجمه متن شما:**\n\n{translated_text}",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard(),
        )
        set_state(chat_id, None)
        return

    # ====== 8. تولید رفرنس BibTeX ======
    if step == "waiting_bibtex_doi":
        doi_input = text.strip()
        await update.message.reply_text("⏳ در حال پردازش اطلاعات مقاله...")

        bibtex_result = get_bibtex_from_openalex(doi_input)

        if not bibtex_result:
            await update.message.reply_text(
                "❌ مقاله‌ای با این DOI یافت نشد یا اطلاعات آن ناقص است."
            )
            return

        log_usage(chat_id, "generate_bibtex")

        await update.message.reply_text(
            f"📜 <b>رفرنس BibTeX شما آماده است:</b>\n\n"
            f"<pre><code>{bibtex_result}</code></pre>\n\n"
            f"💡 این متن را کپی کرده و در نرم‌افزارهای مدیریت رفرنس (مانند Mendeley, EndNote یا LaTeX) استفاده کنید.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )
        set_state(chat_id, None)
        return

    # ====== 9.دانلود کتاب   ======
    if step == "waiting_book_name":
        book_name = text.strip()
        await update.message.reply_text("⏳ در حال جستجوی کتاب در پایگاه داده...")

        books = search_books_by_name(book_name)
        if not books:
            await update.message.reply_text("❌ کتابی با این نام یافت نشد.")
            return

        # ذخیره لیست کتاب‌ها در state برای دانلود بعدی
        set_state(chat_id, "waiting_book_download", books=books)

        msg_text = (
            "📚 **نتایج یافت شده:**\n\nجهت دانلود روی دکمه مربوطه در زیر کلیک کنید👇"
        )
        await update.message.reply_text(
            msg_text,
            parse_mode="Markdown",
            reply_markup=get_books_inline_keyboard(books),
        )
        return
    if not step:
        await update.message.reply_text("لطفاً از منوی اصلی استفاده کنید.")
