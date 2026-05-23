# handlers/channel.py

from telegram import Update
from telegram.ext import ContextTypes

from core.channel_guard import is_channel_member, send_join_channel_message
from core.database import add_user
from core.keyboards import get_main_menu_keyboard
from core.state_manager import clear_state


async def check_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = str(query.message.chat.id)

    if await is_channel_member(context.bot, user.id):
        await query.answer("✅ عضویت شما تأیید شد!", show_alert=True)
        await add_user(chat_id, user.username)
        await clear_state(chat_id)
        await query.message.reply_text(
            "👋 به ربات خوش آمدید!\n\nلطفاً یک گزینه را انتخاب کنید 👇",
            reply_markup=get_main_menu_keyboard(),
        )
    else:
        await query.answer(
            "❌ هنوز در کانال عضو نشده‌اید. پس از عضویت دوباره تلاش کنید.",
            show_alert=True,
        )
        await send_join_channel_message(update, context)
