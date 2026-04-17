# services/book_service.py

import requests


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
