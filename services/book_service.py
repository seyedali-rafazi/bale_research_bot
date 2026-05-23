# services/book_service.py

import io
from urllib.parse import quote

from core.http_client import get_http_session

MAX_BOOK_BYTES = 50 * 1024 * 1024


async def search_books_by_name(query: str, limit: int = 5) -> list[dict]:
    books = []
    session = await get_http_session()

    try:
        url = f"https://www.dbooks.org/api/search/{quote(query)}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("status") == "ok":
                    for item in data.get("books", []):
                        books.append(
                            {
                                "source": "dbooks",
                                "id": item.get("id"),
                                "title": (item.get("title") or "")[:40],
                                "author": (item.get("authors") or "")[:30],
                                "year": "نامشخص",
                                "ext": ".pdf",
                            }
                        )
                        if len(books) >= limit:
                            break
    except Exception as e:
        print(f"Error fetching from dbooks: {e}")

    if len(books) < limit:
        try:
            gut_url = f"https://gutendex.com/books/?search={quote(query)}"
            async with session.get(gut_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("results", []):
                        formats = item.get("formats", {})
                        dl_link = None
                        ext = ""

                        if "application/pdf" in formats:
                            dl_link = formats["application/pdf"]
                            ext = ".pdf"
                        elif "application/epub+zip" in formats:
                            dl_link = formats["application/epub+zip"]
                            ext = ".epub"
                        elif "text/plain; charset=us-ascii" in formats:
                            dl_link = formats["text/plain; charset=us-ascii"]
                            ext = ".txt"

                        if dl_link:
                            author_name = "نامشخص"
                            if item.get("authors"):
                                author_name = item["authors"][0].get("name", "نامشخص")

                            books.append(
                                {
                                    "source": "gutenberg",
                                    "id": str(item.get("id")),
                                    "title": (item.get("title") or "")[:40],
                                    "author": author_name[:30],
                                    "year": "نامشخص",
                                    "link": dl_link,
                                    "ext": ext,
                                }
                            )

                        if len(books) >= limit:
                            break
        except Exception as e:
            print(f"Error fetching from Gutenberg: {e}")

    return books


async def download_book_pdf(book_data: dict) -> io.BytesIO | None:
    try:
        source = book_data.get("source")
        download_url = None
        file_ext = book_data.get("ext", ".pdf")
        session = await get_http_session()

        if source == "dbooks":
            book_id = book_data.get("id")
            details_url = f"https://www.dbooks.org/api/book/{book_id}"
            async with session.get(details_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    download_url = data.get("download")
        elif source == "gutenberg":
            download_url = book_data.get("link")

        if not download_url:
            return None

        async with session.get(download_url) as file_resp:
            if file_resp.status != 200:
                return None

            content_length = file_resp.headers.get("content-length")
            if content_length and int(content_length) > MAX_BOOK_BYTES:
                print("حجم فایل بیشتر از 50 مگابایت است.")
                return None

            raw = await file_resp.read()
            if len(raw) > MAX_BOOK_BYTES:
                print("حجم فایل بیشتر از 50 مگابایت است.")
                return None

            file_stream = io.BytesIO(raw)
            safe_title = "".join(
                x for x in book_data["title"] if x.isalnum() or x in " _-"
            )
            file_stream.name = f"{safe_title[:30]}{file_ext}"
            return file_stream

    except Exception as e:
        print(f"Error downloading book: {e}")

    return None
