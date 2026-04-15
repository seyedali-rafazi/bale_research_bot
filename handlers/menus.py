# handlers/menus.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.state_manager import set_state
from core.constants import *
from core.keyboards import get_article_menu_keyboard

async def btn_back_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .commands import cmd_start
    await cmd_start(update, context)

async def btn_article_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 به بخش جستجوی مقالات خوش آمدید!\nیک گزینه را انتخاب کنید 👇", 
        reply_markup=get_article_menu_keyboard()
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
