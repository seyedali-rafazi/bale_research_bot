# handlers/callbacks.py

from telegram import Update
from telegram.ext import ContextTypes
from core.database import is_vip, get_book_download_count, increment_book_download_count
from core.state_manager import get_state


async def inline_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    data = query.data

    if data.startswith("dlbook_"):
        # بررسی محدودیت کاربر
        if not is_vip(chat_id) and get_book_download_count(chat_id) >= 2:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ شما از محدودیت دانلود کتاب (کلا $ 2 $ بار برای کاربر عادی) استفاده کرده‌اید. لطفا VIP تهیه کنید.",
            )
            return

        index = int(data.split("_")[1])
        state_data = get_state(chat_id)
        books = state_data.get("books", [])

        if index >= len(books):
            await context.bot.send_message(
                chat_id, "❌ خطای سیستمی. لطفا دوباره جستجو کنید."
            )
            return

        selected_book = books[index]

        # ثبت در دیتابیس
        increment_book_download_count(chat_id)

        # در اینجا باید لینک فایل یا داکیومنت کتاب را ارسال کنید
        # چون سورس دانلود مستقیم کتاب متفاوت است، فعلا یک پیام آزمایشی ارسال میشود
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ درخواست دانلود تایید شد!\n\n📕 کتاب: {selected_book['title']}\n👤 نویسنده: {selected_book['author']}\n\n(در این بخش ربات باید فایل PDF را آپلود کند)",
        )
