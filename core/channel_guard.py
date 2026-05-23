# core/channel_guard.py

import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ApplicationHandlerStop, ContextTypes

from core.constants import CB_CHECK_CHANNEL

load_dotenv()

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "").strip()
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

_ACTIVE_MEMBER_STATUSES = frozenset(
    {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER,
    }
)


def channel_guard_enabled() -> bool:
    return bool(REQUIRED_CHANNEL)


def is_admin(user_id: int | str | None) -> bool:
    if user_id is None or not ADMIN_ID:
        return False
    return str(user_id) == ADMIN_ID


async def is_channel_member(bot, user_id: int) -> bool:
    if not channel_guard_enabled():
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in _ACTIVE_MEMBER_STATUSES
    except Exception as e:
        print(f"Channel membership check failed: {e}")
        return False


def get_channel_join_keyboard() -> InlineKeyboardMarkup:
    rows = []
    invite_url = CHANNEL_INVITE_LINK
    if not invite_url and REQUIRED_CHANNEL.startswith("@"):
        invite_url = f"https://t.me/{REQUIRED_CHANNEL[1:]}"
    if invite_url:
        rows.append(
            [InlineKeyboardButton("📢 عضویت در کانال", url=invite_url)]
        )
    rows.append(
        [InlineKeyboardButton("✅ عضو شدم", callback_data=CB_CHECK_CHANNEL)]
    )
    return InlineKeyboardMarkup(rows)


async def send_join_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔒 **دسترسی به ربات فقط برای اعضای کانال فعال است.**\n\n"
        "لطفاً ابتدا در کانال ما عضو شوید، سپس روی دکمه **«عضو شدم»** بزنید."
    )
    keyboard = get_channel_join_keyboard()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )
    elif update.message:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard
        )


def _is_exempt_update(update: Update) -> bool:
    if not update.effective_user:
        return True

    if is_admin(update.effective_user.id):
        return True

    if update.callback_query and update.callback_query.data == CB_CHECK_CHANNEL:
        return True

    message = update.message or update.edited_message
    if message and message.text:
        text = message.text.split()[0]
        if text.startswith("/start"):
            return True

    return False


async def should_allow_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not channel_guard_enabled():
        return True
    if _is_exempt_update(update):
        return True
    user = update.effective_user
    if not user:
        return True
    return await is_channel_member(context.bot, user.id)


async def channel_membership_guard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if await should_allow_user(update, context):
        return
    await send_join_channel_message(update, context)
    raise ApplicationHandlerStop()
