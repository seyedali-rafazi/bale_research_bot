# services/openalex.py

import re
from typing import Any, Optional

from core.http_client import get_http_session

OPENALEX_HEADERS = {"User-Agent": "BaleBot/2.0"}


def clean_doi(doi: str) -> str:
    if not doi:
        return ""
    return re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi).strip()


def format_openalex_item(item) -> dict:
    title = item.get("title", "بدون عنوان") or "بدون عنوان"

    authors_list = item.get("authorships", [])
    author_names = ", ".join(
        a.get("author", {}).get("display_name", "") for a in authors_list[:3]
    )
    if len(authors_list) > 3:
        author_names += " و همکاران"

    doi = item.get("doi", "ندارد")
    if doi and doi != "ندارد":
        doi = clean_doi(doi)

    year = item.get("publication_year", "نامشخص")
    citations = item.get("cited_by_count", 0)

    pdf_urls = []
    for loc in item.get("locations", []):
        pdf_url = loc.get("pdf_url")
        if pdf_url and pdf_url not in pdf_urls:
            pdf_urls.append(pdf_url)

    is_oa = item.get("open_access", {}).get("is_oa", False)

    return {
        "title": title,
        "authors": author_names if author_names else "نامشخص",
        "doi": doi,
        "year": str(year),
        "citations": citations,
        "is_oa": is_oa,
        "pdf_urls": pdf_urls,
    }


async def fetch_work_by_doi(doi_input: str) -> Optional[dict[str, Any]]:
    doi_clean = clean_doi(doi_input)
    if not doi_clean:
        return None

    url = f"https://api.openalex.org/works/https://doi.org/{doi_clean}"
    session = await get_http_session()
    try:
        async with session.get(url, headers=OPENALEX_HEADERS) as response:
            if response.status == 200:
                return await response.json()
    except Exception as e:
        print(f"Error fetching OpenAlex work: {e}")
    return None


async def search_works(
    query: str,
    page: int = 1,
    min_year: Optional[int] = None,
    sort_by: str = "relevance",
) -> list[dict]:
    params = {"search": query, "per-page": 5, "page": page}
    if sort_by == "citation":
        params["sort"] = "cited_by_count:desc"
    if min_year:
        params["filter"] = f"from_publication_date:{min_year}-01-01"

    session = await get_http_session()
    try:
        async with session.get(
            "https://api.openalex.org/works",
            params=params,
            headers=OPENALEX_HEADERS,
        ) as response:
            response.raise_for_status()
            data = await response.json()
            results = []
            for item in data.get("results", []):
                formatted = format_openalex_item(item)
                if formatted:
                    results.append(formatted)
            return results
    except Exception as e:
        print(f"Error searching OpenAlex: {e}")
        return []


async def search_article_by_doi(doi_input: str) -> list[dict]:
    data = await fetch_work_by_doi(doi_input)
    if data:
        return [format_openalex_item(data)]
    return []


async def get_article_data_for_citation(doi_input: str) -> Optional[dict]:
    data = await fetch_work_by_doi(doi_input)
    if not data:
        return None

    title = data.get("title", "Unknown Title")
    year = str(data.get("publication_year", "Unknown Year"))
    doi_val = clean_doi(data.get("doi", ""))

    journal = "Unknown Journal"
    primary_location = data.get("primary_location")
    if primary_location and primary_location.get("source"):
        journal = primary_location["source"].get("display_name", "Unknown Journal")

    authors_list = []
    for authorship in data.get("authorships", []):
        author_name = authorship.get("author", {}).get("display_name")
        if author_name:
            authors_list.append(author_name)

    return {
        "title": title,
        "year": year,
        "doi": doi_val,
        "journal": journal,
        "authors_list": authors_list,
    }


async def get_abstract_from_openalex(doi_input: str) -> Optional[str]:
    data = await fetch_work_by_doi(doi_input)
    if not data:
        return None

    idx = data.get("abstract_inverted_index", {})
    if not idx:
        return None

    words = []
    for word, positions in idx.items():
        for pos in positions:
            words.append((pos, word))
    words.sort(key=lambda x: x[0])
    return " ".join(w[1] for w in words)


async def get_bibtex_from_openalex(doi_input: str) -> Optional[str]:
    data = await fetch_work_by_doi(doi_input)
    if not data:
        return None

    title = data.get("title", "Unknown Title")
    year = str(data.get("publication_year", "Unknown Year"))
    doi_val = clean_doi(data.get("doi", "Unknown_DOI"))

    authors_list = []
    for authorship in data.get("authorships", []):
        author_name = authorship.get("author", {}).get("display_name")
        if author_name:
            authors_list.append(author_name)
    authors_str = " and ".join(authors_list)

    journal = "Unknown Journal"
    primary_location = data.get("primary_location")
    if primary_location and primary_location.get("source"):
        journal = primary_location["source"].get("display_name", "Unknown Journal")

    bib_key = f"{doi_val.split('/')[-1]}_{year}".replace(".", "_").replace("-", "_")
    return (
        f"@article{{{bib_key},\n"
        f"  title={{{title}}},\n"
        f"  author={{{authors_str}}},\n"
        f"  journal={{{journal}}},\n"
        f"  year={{{year}}},\n"
        f"  doi={{{doi_val}}}\n"
        f"}}"
    )
