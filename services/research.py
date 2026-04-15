import requests
from bs4 import BeautifulSoup

def search_article_by_name(query):
    url = f"https://api.crossref.org/works?query.title={query}&rows=5&select=DOI,title,author,URL,publisher"
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
        
        authors_list = item.get('author', [])
        authors = ", ".join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list[:3]])
        if len(authors_list) > 3:
            authors += " et al."
                
        results.append({
            'title': title,
            'doi': doi,
            'authors': authors if authors else "Unknown",
            'publisher': publisher,
            'url': url
        })
    return results

def get_scihub_pdf_url(doi):
    # دامنه‌های فعال سای هاب
    base_urls = ['https://sci-hub.se/', 'https://sci-hub.ru/', 'https://sci-hub.st/']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for base in base_urls:
        try:
            target_url = f"{base}{doi}"
            res = requests.get(target_url, headers=headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                pdf_embed = soup.find('embed', {'type': 'application/pdf'})
                pdf_iframe = soup.find('iframe', {'id': 'pdf'})
                
                pdf_url = None
                if pdf_embed and pdf_embed.get('src'):
                    pdf_url = pdf_embed['src']
                elif pdf_iframe and pdf_iframe.get('src'):
                    pdf_url = pdf_iframe['src']
                    
                if pdf_url:
                    if pdf_url.startswith('//'):
                        return 'https:' + pdf_url
                    elif pdf_url.startswith('/'):
                        return base.rstrip('/') + pdf_url
                    return pdf_url
        except Exception as e:
            continue
    return None

def download_pdf(url, filename):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200 and 'pdf' in res.headers.get('Content-Type', '').lower():
            filepath = f"{filename}.pdf"
            with open(filepath, 'wb') as f:
                f.write(res.content)
            return filepath
    except Exception as e:
        print(f"Download Error: {e}")
    return None
