# handlers/callbacks.py

from telegram import Update
from telegram.ext import ContextTypes
from core.database import is_vip, get_book_download_count, increment_book_download_count
from core.state_manager import get_state
from services.book_service import download_book_pdf


async def inline_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = str(query.message.chat.id)
    data = query.data

    if data.startswith("dlbook_"):
        if not is_vip(chat_id) and get_book_download_count(chat_id) >= 2:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ شما از محدودیت دانلود کتاب (کلا $ 2 $ بار برای کاربر عادی) استفاده کرده‌اید. لطفا از منوی اصلی VIP تهیه کنید.",
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

        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ در حال آماده‌سازی و آپلود فایل PDF. لطفاً صبور باشید...",
        )

        # دریافت فایل PDF از سرویس دانلود
        pdf_file = await download_book_pdf(selected_book["title"])

        if pdf_file:
            # ثبت یک بار دانلود در دیتابیس
            increment_book_download_count(chat_id)

            caption = f"📕 **عنوان:** {selected_book['title']}\n👤 **نویسنده:** {selected_book['author']}"

            # آپلود فایل برای کاربر
            await context.bot.send_document(
                chat_id=chat_id,
                document=pdf_file,
                caption=caption,
                parse_mode="Markdown",
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ متاسفانه در دانلود این کتاب مشکلی پیش آمد.")
