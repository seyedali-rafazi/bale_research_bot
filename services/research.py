import requests

def search_article_by_name(query):
    url = f"https://api.crossref.org/works?query.title={query}&rows=5&select=DOI,title,author,URL,link,publisher"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        items = data.get('message', {}).get('items', [])
        return process_crossref_items(items)
    except Exception as e:
        print(f"Error: {e}")
        return []

def search_article_by_doi(doi):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            item = res.json().get('message', {})
            return process_crossref_items([item])
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def process_crossref_items(items):
    results = []
    for item in items:
        title = item.get('title', ['Unknown Title'])[0]
        doi = item.get('DOI', 'No DOI')
        url = item.get('URL', '')
        publisher = item.get('publisher', 'Unknown Publisher')
        
        # استخراج نام نویسندگان
        authors_list = item.get('author', [])
        authors = ", ".join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list[:3]])
        if len(authors_list) > 3:
            authors += " et al."
            
        # جستجوی لینک مستقیم PDF در دیتا
        pdf_url = None
        links = item.get('link', [])
        for link in links:
            if link.get('content-type') == 'application/pdf':
                pdf_url = link.get('URL')
                break
                
        results.append({
            'title': title,
            'doi': doi,
            'authors': authors if authors else "Unknown",
            'publisher': publisher,
            'url': url,
            'pdf_url': pdf_url
        })
    return results

def download_pdf(url, filename):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200 and 'application/pdf' in res.headers.get('Content-Type', ''):
            filepath = f"{filename}.pdf"
            with open(filepath, 'wb') as f:
                f.write(res.content)
            return filepath
    except Exception as e:
        print(f"Download Error: {e}")
    return None
