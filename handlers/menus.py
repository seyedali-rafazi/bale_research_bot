# handlers/menus.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import set_state
from core.constants import *
from core.keyboards import get_article_menu_keyboard
from core.database import (
    is_vip,
    get_user_total_usage,
    get_citation_count,
    get_user_usage_today,
)


async def btn_back_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .commands import cmd_start

    await cmd_start(update, context)


async def btn_article_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 **به بخش جستجوی مقالات خوش آمدید!**\n\n"
        "💡 **راهنمای جستجو:**\n"
        "🔹 **جستجو با DOI:** ربات تلاش می‌کند مقاله را از پایگاه **Sci-Hub** دانلود کند (بهترین روش برای مقالات پولی و غیررایگان).\n"
        "🔹 **جستجو بر اساس نام:** ربات در پایگاه **OpenAlex** جستجو کرده و مقالاتی که نسخه رایگان (Open Access) دارند را برای شما پیدا می‌کند.\n\n"
        "یک گزینه را انتخاب کنید 👇"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=get_article_menu_keyboard()
    )


async def btn_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_is_vip = is_vip(chat_id)
    status_text = "VIP 🌟" if user_is_vip else "عادی 👤"
    total_usage = get_user_total_usage(chat_id)

    text = (
        f"👤 **اطلاعات حساب کاربری شما:**\n\n"
        f"🆔 آیدی عددی: `{chat_id}`\n"
        f"🔰 نوع پروفایل: {status_text}\n"
        f"📥 دفعات استفاده از ربات: $ {total_usage} $ بار"
    )
    await update.message.reply_text(text)


async def btn_support_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    set_state(chat_id, "waiting_support_message")
    await update.message.reply_text(
        "🎧 لطفاً پیام خود را برای پشتیبانی بنویسید تا به ادمین ارسال شود:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )


async def btn_search_doi_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    set_state(chat_id, "waiting_article_doi")

    text = (
        "🔍 **لطفاً شناسه DOI مقاله مورد نظر را بفرستید.**\n\n"
        "شما می‌توانید شناسه را به هر دو شکل زیر (لینک کامل یا فقط کد) ارسال کنید:\n\n"
        "🔸 **فقط کد:**\n"
        "`10.1364/oe.21.004958`\n"
        "🔸 **لینک کامل:**\n"
        "`https://doi.org/10.1364/oe.21.004958`"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )


async def btn_search_name_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    set_state(chat_id, "waiting_article_name")
    await update.message.reply_text(
        "🔎 لطفاً نام مقاله یا کلمات کلیدی آن را وارد کنید:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )


# --- تابع جدید برای دکمه تولید رفرنس ---
async def btn_citation_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # بررسی محدودیت استفاده (کاربر عادی حداکثر 3 بار)
    if not is_vip(chat_id) and get_citation_count(chat_id) >= 3:
        await update.message.reply_text(
            "❌ شما از تمام ظرفیت ($ 3 $ رفرنس) اکانت عادی خود استفاده کرده‌اید.\nبرای استفاده نامحدود، از طریق منوی اصلی حساب خود را VIP کنید."
        )
        return

    set_state(chat_id, "waiting_for_citation_doi")
    text = (
        "📑 **لطفاً شناسه DOI مقاله مورد نظر را جهت تولید رفرنس ارسال کنید:**\n\n"
        "💡 (می‌توانید هم لینک کامل و هم شناسه خالی را بفرستید)\n"
        "مثال‌ها:\n"
        "`10.1038/nature12373`\n"
        "`https://doi.org/10.1038/nature12373`"
    )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )


# --- تابع جدید برای دکمه چکیده هوشمند ---
async def btn_smart_abstract_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    # بررسی محدودیت استفاده
    user_is_vip = is_vip(chat_id)
    daily_limit = 10 if user_is_vip else 2
    usage_today = get_user_usage_today(chat_id, "smart_abstract")

    if usage_today >= daily_limit:
        await update.message.reply_text(
            f"❌ شما به سقف مجاز روزانه خود ($ {daily_limit} $) بار رسیده‌اید.\nبرای افزایش محدودیت می‌توانید حساب خود را VIP کنید."
        )
        return

    set_state(chat_id, "waiting_smart_abstract_doi")

    message_text = (
        "🧠 **به بخش چکیده هوشمند خوش آمدید!**\n\n"
        "در این بخش می‌توانید شناسه مقاله مورد نظر خود را ارسال کنید تا هوش مصنوعی چکیده آن را استخراج کرده و تحلیل جامعی از نکات کلیدی آن به شما ارائه دهد.\n\n"
        "✅ **فرمت‌های قابل پشتیبانی:**\n"
        "شما می‌توانید DOI را به هر دو شکل زیر ارسال کنید:\n"
        "🔗 **لینک کامل:**\n"
        "`https://doi.org/10.1364/oe.21.004958`\n"
        "🔢 **فقط شناسه:**\n"
        "`10.1364/oe.21.004958`\n\n"
        "👇 لطفاً DOI مقاله خود را ارسال کنید:"
    )

    await update.message.reply_text(
        message_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )


async def btn_translate_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if not is_vip(chat_id):
        usage_today = get_user_usage_today(chat_id, "translate_text")
        if usage_today >= 2:
            await update.message.reply_text(
                "❌ کاربر عادی عزیز، شما از تمام ظرفیت روزانه ($ 2 $ بار) برای ابزار **ترجمه متن** استفاده کرده‌اید.\nبرای استفاده نامحدود، اکانت خود را VIP کنید."
            )
            return

    set_state(chat_id, "waiting_translate_text")
    await update.message.reply_text(
        "🇮🇷 **به بخش ترجمه متون علمی خوش آمدید!**\n\n"
        "لطفاً متن انگلیسی مورد نظر خود را بفرستید تا با دقت بالا به فارسی ترجمه شود:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )


async def btn_bibtex_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    if not is_vip(chat_id):
        usage_today = get_user_usage_today(chat_id, "generate_bibtex")
        if usage_today >= 2:
            await update.message.reply_text(
                "❌ کاربر عادی عزیز، شما از تمام ظرفیت روزانه ($ 2 $ بار) برای ابزار **تولید BibTeX** استفاده کرده‌اید.\nبرای استفاده نامحدود، اکانت خود را VIP کنید."
            )
            return

    set_state(chat_id, "waiting_bibtex_doi")
    await update.message.reply_text(
        "📜 **به بخش تولید فایل BibTeX خوش آمدید!**\n\n"
        "لطفاً شناسه DOI مقاله مورد نظر را ارسال کنید (مثال: `10.1038/nature12373`):",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
        parse_mode="Markdown",
    )


async def btn_book_search_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    set_state(chat_id, "waiting_book_name")
    await update.message.reply_text(
        "📕 لطفاً نام کتاب مورد نظر خود را (ترجیحاً به انگلیسی) ارسال کنید:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(BTN_BACK)]], resize_keyboard=True
        ),
    )
