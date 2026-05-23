# services/research.py

import asyncio
import os

from core.http_client import get_http_session
from core.telethon_client import (
    SCIHUB_BOT_USERNAME,
    scihub_configured,
    scihub_semaphore,
    get_telethon_client,
    wait_for_message,
    _is_pdf_attachment,
)
from services.openalex import clean_doi, search_works, search_article_by_doi

UNPAYWALL_EMAIL = os.getenv("UNPAYWALL_EMAIL", "contact@example.com")
PDF_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


async def search_article_by_name(query, page=1, min_year=None, sort_by="relevance"):
    return await search_works(query, page=page, min_year=min_year, sort_by=sort_by)


async def get_unpaywall_pdf(doi: str) -> str | None:
    url = f"https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}"
    session = await get_http_session()
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                best = data.get("best_oa_location")
                if best:
                    return best.get("url_for_pdf")
    except Exception:
        pass
    return None


async def get_semanticscholar_pdf(doi: str) -> str | None:
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf"
    session = await get_http_session()
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                oa = data.get("openAccessPdf")
                if oa:
                    return oa.get("url")
    except Exception:
        pass
    return None


async def _write_pdf_file(file_path: str, data: bytes) -> bool:
    if len(data) <= 10240:
        return False
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    def _write():
        with open(file_path, "wb") as f:
            f.write(data)

    await asyncio.to_thread(_write)
    return os.path.exists(file_path) and os.path.getsize(file_path) > 10240


async def download_direct_pdf(url: str, doi_or_name: str) -> str | None:
    if not url:
        return None

    safe_name = doi_or_name.replace("/", "_").replace("\\", "_")
    file_path = f"downloads/{safe_name}_direct.pdf"

    session = await get_http_session()
    try:
        async with session.get(url, headers=PDF_HEADERS) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if response.status != 200 or "application/pdf" not in content_type:
                return None
            data = await response.read()

        if await _write_pdf_file(file_path, data):
            return file_path
        if os.path.exists(file_path):
            await asyncio.to_thread(os.remove, file_path)
    except Exception as e:
        print(f"Error downloading direct PDF from {url}: {e}")
    return None


async def download_pdf_via_telegram(doi_input: str) -> str | None:
    if not scihub_configured():
        return None

    doi = clean_doi(doi_input)
    if not doi:
        return None

    async with scihub_semaphore:
        client = await get_telethon_client()
        if not client:
            print("⚠️ Telethon session is not authorized.")
            return None

        try:
            sent = await client.send_message(SCIHUB_BOT_USERNAME, doi)
            msg = await wait_for_message(
                client,
                SCIHUB_BOT_USERNAME,
                timeout=float(os.getenv("SCIHUB_REPLY_TIMEOUT", "45")),
                after_id=sent.id,
                predicate=_is_pdf_attachment,
            )
            if not msg:
                return None

            os.makedirs("downloads", exist_ok=True)
            safe_name = doi.replace("/", "_").replace("\\", "_")
            file_path = f"downloads/{safe_name}.pdf"
            await client.download_media(message=msg, file=file_path)
            return file_path if os.path.exists(file_path) else None
        except Exception as e:
            print(f"Error in Telegram fetch: {e}")
            return None


async def smart_download_pdf(article: dict, status_message) -> str | None:
    doi = article.get("doi")
    is_oa = article.get("is_oa")

    if is_oa:
        await status_message.edit_text(
            "ℹ️ این مقاله رایگان (Open Access) است. در حال بررسی منابع مختلف..."
        )

    await status_message.edit_text("🔍 تلاش اول: جستجو در مخازن OpenAlex...")
    for pdf_url in article.get("pdf_urls", []):
        file_path = await download_direct_pdf(pdf_url, doi or "article")
        if file_path:
            return file_path

    if not doi or doi == "ندارد":
        return None

    await status_message.edit_text("🔍 تلاش دوم: جستجو در پایگاه Unpaywall...")
    unpaywall_url = await get_unpaywall_pdf(doi)
    if unpaywall_url:
        file_path = await download_direct_pdf(unpaywall_url, doi)
        if file_path:
            return file_path

    await status_message.edit_text("🔍 تلاش سوم: جستجو در پایگاه Semantic Scholar...")
    semantic_url = await get_semanticscholar_pdf(doi)
    if semantic_url:
        file_path = await download_direct_pdf(semantic_url, doi)
        if file_path:
            return file_path

    if not scihub_configured():
        await status_message.edit_text(
            "⚠️ تنظیمات Sci-Hub برای تلگرام کامل نیست؛ این مرحله نادیده گرفته شد."
        )
        return None

    await status_message.edit_text(
        "🤖 تلاش چهارم: درخواست از Sci-Hub (ممکن است کمی طول بکشد)..."
    )
    file_path = await download_pdf_via_telegram(doi)
    if file_path:
        return file_path

    await status_message.edit_text(
        "❌ متاسفانه فایل PDF در هیچ‌یک از منابع یافت نشد."
    )
    return None


async def get_article_data_for_citation(doi_input: str) -> dict | None:
    from services.openalex import get_article_data_for_citation as _get

    return await _get(doi_input)
