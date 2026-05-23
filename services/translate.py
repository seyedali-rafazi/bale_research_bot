# services/translate.py

import asyncio

from googletrans import Translator

_translator = Translator()


async def translate_text(text: str, src: str = "auto", dest: str = "fa") -> str:
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _translator.translate(text, src=src, dest=dest),
        )
        if result and result.text:
            return result.text
        return "❌ ترجمه خالی برگشت. لطفاً متن دیگری ارسال کنید."
    except Exception as e:
        print(f"Google translate error: {e}")
        return "❌ خطا در ترجمه متن. لطفاً بعداً دوباره تلاش کنید."
