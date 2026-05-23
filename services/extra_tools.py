# services/extra_tools.py

from core.telethon_client import (
    CHATGPT_BOT_USERNAME,
    ai_bot_configured,
    ai_semaphore,
    get_telethon_client,
    wait_for_message,
    _is_bot_text_reply,
)
from services.openalex import get_bibtex_from_openalex

__all__ = ["get_bibtex_from_openalex", "translate_text_with_ai"]


async def translate_text_with_ai(text: str) -> str:
    if not ai_bot_configured():
        return "⚠️ خطا: تنظیمات ربات هوش مصنوعی در سرور کامل نیست."

    async with ai_semaphore:
        client = await get_telethon_client()
        if not client:
            return "⚠️ خطا: اکانت تلگرام سرور لاگین نیست."

        try:
            prompt = (
                "لطفاً متن انگلیسی زیر را با دقت و به صورت روان و تخصصی به فارسی ترجمه کن. "
                "فقط متن ترجمه شده را برگردان و هیچ سوال یا توضیح اضافه‌ای ننویس:\n\n"
                f"{text}"
            )
            sent = await client.send_message(CHATGPT_BOT_USERNAME, prompt)

            msg = await wait_for_message(
                client,
                CHATGPT_BOT_USERNAME,
                timeout=90.0,
                after_id=sent.id,
                predicate=lambda m: _is_bot_text_reply(m, 5),
            )
            if msg and msg.text:
                return msg.text

            return "❌ زمان انتظار برای ترجمه پایان یافت یا ربات مبدا پاسخی نداد."
        except Exception as e:
            print(f"Error in translation: {e}")
            return "❌ خطا در برقراری ارتباط با هوش مصنوعی برای ترجمه."
