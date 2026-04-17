# services/book_service.py

import requests
import io


def search_books_by_name(query: str, limit: int = 5):
    url = f"https://openlibrary.org/search.json?q={query}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            books = []
            for doc in data.get("docs", []):
                books.append(
                    {
                        "title": doc.get("title", "نامشخص"),
                        "author": doc.get("author_name", ["نامشخص"])[0],
                        "year": doc.get("first_publish_year", "نامشخص"),
                        "key": doc.get("key", ""),
                    }
                )
            return books
    except Exception as e:
        print(f"Error fetching books: {e}")
    return []


async def download_book_pdf(book_title: str) -> io.BytesIO:
    """
    این تابع باید به API دانلود کتاب متصل شود (مثلا LibGen).
    در حال حاضر یک فایل PDF تستی تولید میکند تا ساختار آپلود کار کند.
    """
    # ساخت یک فایل PDF ساده در حافظه (RAM)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n4 0 obj\n<< /Length 56 >>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(This is a placeholder PDF file!) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000288 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n393\n%%EOF"

    file_stream = io.BytesIO(pdf_content)
    # اسم فایل که کاربر هنگام دانلود میبیند
    safe_title = "".join(x for x in book_title if x.isalnum() or x in " _-")
    file_stream.name = f"{safe_title[:30]}.pdf"

    return file_stream
