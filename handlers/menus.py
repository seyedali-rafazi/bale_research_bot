#handlers/menus.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import set_state
from core.constants import *
from core.keyboards import get_article_menu_keyboard
from core.database import is_vip, get_user_total_usage, get_citation_count, get_user_usage_today


async def btn_back_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .commands import cmd_start
    await cmd_start(update, context)

async def btn_article_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 به بخش جستجوی مقالات خوش آمدید!\nیک گزینه را انتخاب کنید 👇", 
        reply_markup=get_article_menu_keyboard()
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
    set_state(chat_id, 'waiting_support_message')
    await update.message.reply_text(
        "🎧 لطفاً پیام خود را برای پشتیبانی بنویسید تا به ادمین ارسال شود:", 
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    )

async def btn_search_doi_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    set_state(chat_id, 'waiting_article_doi')
    await update.message.reply_text(
        "🔍 لطفاً شناسه DOI مقاله را بفرستید (مثال: 10.1038/nature12373):", 
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    )

async def btn_search_name_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    set_state(chat_id, 'waiting_article_name')
    await update.message.reply_text(
        "🔎 لطفاً نام مقاله یا کلمات کلیدی آن را وارد کنید:", 
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    )

# --- تابع جدید برای دکمه تولید رفرنس ---
async def btn_citation_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    # بررسی محدودیت استفاده (کاربر عادی حداکثر 3 بار)
    if not is_vip(chat_id) and get_citation_count(chat_id) >= 3:
        await update.message.reply_text("❌ شما از تمام ظرفیت ($ 3 $ رفرنس) اکانت عادی خود استفاده کرده‌اید.\nبرای استفاده نامحدود، از طریق منوی اصلی حساب خود را VIP کنید.")
        return

    set_state(chat_id, 'waiting_for_citation_doi')
    await update.message.reply_text(
        "📑 لطفاً شناسه DOI مقاله مورد نظر را جهت تولید رفرنس ارسال کنید:\n(مثال: `10.1038/nature12373`)", 
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    )

# --- تابع جدید برای دکمه چکیده هوشمند ---
async def btn_smart_abstract_req(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    # بررسی محدودیت استفاده
    user_is_vip = is_vip(chat_id)
    daily_limit = 10 if user_is_vip else 2
    usage_today = get_user_usage_today(chat_id, "smart_abstract")
    
    if usage_today >= daily_limit:
        await update.message.reply_text(f"❌ شما به سقف مجاز روزانه خود ($ {daily_limit} $) بار رسیده‌اید.\nبرای افزایش محدودیت می‌توانید حساب خود را VIP کنید.")
        return

    set_state(chat_id, 'waiting_smart_abstract_doi')
    
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
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(BTN_BACK)]], resize_keyboard=True)
    )
