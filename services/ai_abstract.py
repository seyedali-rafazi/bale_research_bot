# services/ai_abstract.py

from core.telethon_client import (
    CHATGPT_BOT_USERNAME,
    ai_bot_configured,
    ai_semaphore,
    get_telethon_client,
    wait_for_message,
    _is_bot_text_reply,
)
from services.openalex import get_abstract_from_openalex

__all__ = ["get_abstract_from_openalex", "analyze_abstract_with_ai"]


async def analyze_abstract_with_ai(abstract_text: str) -> str:
    if not ai_bot_configured():
        return "⚠️ خطا: تنظیمات ربات هوش مصنوعی در سرور کامل نیست."

    async with ai_semaphore:
        client = await get_telethon_client()
        if not client:
            return "⚠️ خطا: اکانت تلگرام سرور لاگین نیست."

        try:
            prompt = (
                "لطفا این چکیده علمی را به طور کامل تحلیل کن و نکات کلیدی آن را بیان کن. "
                "نکته بسیار مهم: در انتهای پاسخ خود به هیچ وجه سوالی نپرس "
                "و فقط و فقط متن تحلیل را به صورت مستقیم ارائه بده:\n\n"
                f"{abstract_text}"
            )
            sent = await client.send_message(CHATGPT_BOT_USERNAME, prompt)

            msg = await wait_for_message(
                client,
                CHATGPT_BOT_USERNAME,
                timeout=120.0,
                after_id=sent.id,
                predicate=lambda m: _is_bot_text_reply(m, 20),
            )
            if msg and msg.text:
                return msg.text

            return "❌ زمان انتظار برای تحلیل پایان یافت یا ربات مبدا پاسخی نداد."
        except Exception as e:
            print(f"Error in AI abstract analysis: {e}")
            return "❌ خطا در برقراری ارتباط با هوش مصنوعی."
