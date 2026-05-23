# core/http_client.py

import os
from typing import Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=int(os.getenv("HTTP_TIMEOUT_SECONDS", "15")))
HTTP_CONNECT_LIMIT = int(os.getenv("HTTP_CONNECT_LIMIT", "100"))
HTTP_CONNECT_PER_HOST = int(os.getenv("HTTP_CONNECT_PER_HOST", "30"))

_session: Optional[aiohttp.ClientSession] = None


async def get_http_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(
            limit=HTTP_CONNECT_LIMIT,
            limit_per_host=HTTP_CONNECT_PER_HOST,
            ttl_dns_cache=300,
        )
        _session = aiohttp.ClientSession(
            connector=connector,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": "BaleBot/2.0"},
        )
    return _session


async def close_http_session():
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
        _session = None
