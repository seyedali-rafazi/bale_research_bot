import io
import requests
from bs4 import BeautifulSoup
import urllib.parse


def search_books_by_name(query: str, limit: int = 5):
    """
    جستجوی واقعی کتاب با تست دامنه‌های مختلف LibGen
    """
    # لیستی از دامنه‌های فعال لیب‌جن
    mirrors = [
        "http://libgen.im",
        "http://libgen.is",
        "http://libgen.st",
        "http://libgen.li",
    ]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    books = []

    for mirror in mirrors:
        url = f"{mirror}/search.php?req={urllib.parse.quote(query)}&res=25&view=simple&phrase=1&column=def"
        try:
            print(f"Trying to connect to {mirror} ...")
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table", class_="c")
                if not table:
                    continue  # سایت باز شده اما جدولی نیست، شاید کپچا باشد

                rows = table.find_all("tr")[1:]

                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 10:
                        ext = cols[8].text.strip().lower()
                        if ext != "pdf":
                            continue

                        author = cols[1].text.strip()
                        title_col = cols[2]
                        title_a = title_col.find_all("a")
                        title = title_a[0].text.strip() if title_a else "نامشخص"
                        year = cols[4].text.strip()

                        md5_link = ""
                        mirror_links = cols[9].find_all("a")
                        if mirror_links:
                            md5_link = mirror_links[0].get("href", "")
                            # در صورتی که لینک نسبی باشد، آن را کامل میکنیم
                            if md5_link.startswith("/"):
                                md5_link = "http://library.lol" + md5_link

                        books.append(
                            {
                                "title": title,
                                "author": author[:50],
                                "year": year,
                                "link": md5_link,
                            }
                        )

                        if len(books) >= limit:
                            break

                # اگر با این دامنه موفق به دریافت لیست شدیم، از حلقه خارج می‌شویم
                if books:
                    print(f"Successfully fetched from {mirror}")
                    break

        except Exception as e:
            print(f"Failed to connect to {mirror}: {e}")
            continue  # دامنه بعدی را تست کن

    return books


async def download_book_pdf(book_data: dict) -> io.BytesIO:
    """
    دریافت فایل واقعی PDF از لینک LibGen
    """
    try:
        download_page_url = book_data.get("link")
        if not download_page_url:
            return None

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        # 1. ورود به صفحه دانلود (library.lol) برای استخراج لینک مستقیم
        page_resp = requests.get(download_page_url, headers=headers, timeout=15)
        if page_resp.status_code != 200:
            return None

        soup = BeautifulSoup(page_resp.text, "html.parser")
        download_link_tag = soup.find("a", string="GET") or soup.select_one(
            "#download h2 a"
        )

        if not download_link_tag:
            return None

        direct_link = download_link_tag.get("href")

        # 2. دانلود فایل PDF
        pdf_resp = requests.get(direct_link, headers=headers, timeout=60, stream=True)
        if pdf_resp.status_code == 200:
            # بررسی حجم فایل (تلگرام اجازه ارسال فایل بیشتر از 50 مگابایت را به ربات‌های معمولی نمی‌دهد)
            content_length = pdf_resp.headers.get("content-length")
            if content_length and int(content_length) > 50 * 1024 * 1024:
                print("حجم فایل بیشتر از 50 مگابایت است.")
                return None

            file_stream = io.BytesIO(pdf_resp.content)
            safe_title = "".join(
                x for x in book_data["title"] if x.isalnum() or x in " _-"
            )
            file_stream.name = f"{safe_title[:30]}.pdf"

            return file_stream

    except Exception as e:
        print(f"Error downloading PDF: {e}")

    return None
