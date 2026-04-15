# handlers/commands.py

from telegram import Update
from telegram.ext import ContextTypes
from core.state_manager import clear_state, set_state
from core.keyboards import get_main_menu_keyboard
from core.constants import BTN_BACK
from core.database import add_user


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    username = update.effective_chat.username
    
    # ثبت کاربر در دیتابیس (اگر قبلا نباشد اضافه میشود)
    add_user(chat_id, username)
    
    clear_state(chat_id)
    await update.message.reply_text(
        "👋 به ربات خوش آمدید!\n\nلطفاً یک گزینه را انتخاب کنید 👇",
        reply_markup=get_main_menu_keyboard()
    )

