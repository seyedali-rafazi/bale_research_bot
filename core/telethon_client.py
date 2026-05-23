# core/telethon_client.py

import asyncio
import os
from typing import Callable, Optional

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message

load_dotenv()

API_ID = int(os.getenv("API_ID", "0") or "0")
API_HASH = os.getenv("API_HASH", "")
SESSION_NAME = os.getenv("SESSION_NAME", "")
SCIHUB_BOT_USERNAME = os.getenv("SCIHUB_BOT_USERNAME", "")
CHATGPT_BOT_USERNAME = os.getenv("CHATGPT_BOT_USERNAME", "")

TELETHON_SCIHUB_CONCURRENCY = int(os.getenv("TELETHON_SCIHUB_CONCURRENCY", "3"))
TELETHON_AI_CONCURRENCY = int(os.getenv("TELETHON_AI_CONCURRENCY", "5"))

_client: Optional[TelegramClient] = None
_connect_lock = asyncio.Lock()
scihub_semaphore = asyncio.Semaphore(TELETHON_SCIHUB_CONCURRENCY)
ai_semaphore = asyncio.Semaphore(TELETHON_AI_CONCURRENCY)


def telethon_configured() -> bool:
    return bool(API_ID and API_HASH and SESSION_NAME)


def scihub_configured() -> bool:
    return telethon_configured() and bool(SCIHUB_BOT_USERNAME)


def ai_bot_configured() -> bool:
    return telethon_configured() and bool(CHATGPT_BOT_USERNAME)


async def get_telethon_client() -> Optional[TelegramClient]:
    if not telethon_configured():
        return None

    global _client
    async with _connect_lock:
        if _client is None:
            _client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        if not _client.is_connected():
            await _client.connect()
        if not await _client.is_user_authorized():
            return None
    return _client


async def close_telethon_client():
    global _client
    if _client is not None:
        if _client.is_connected():
            await _client.disconnect()
        _client = None


async def wait_for_message(
    client: TelegramClient,
    peer: str,
    *,
    timeout: float = 60.0,
    after_id: int = 0,
    predicate: Optional[Callable[[Message], bool]] = None,
) -> Optional[Message]:
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    async def _handler(event):
        if future.done():
            return
        msg = event.message
        if after_id and msg.id <= after_id:
            return
        if predicate is None or predicate(msg):
            future.set_result(msg)

    client.add_event_handler(_handler, events.NewMessage(chats=peer))
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        client.remove_event_handler(_handler, events.NewMessage)


def _is_bot_text_reply(msg: Message, min_len: int) -> bool:
    return bool(
        msg.text
        and not msg.out
        and not msg.sticker
        and len(msg.text.strip()) >= min_len
    )


def _is_pdf_attachment(msg: Message) -> bool:
    return bool(msg.file and msg.file.ext == ".pdf")
