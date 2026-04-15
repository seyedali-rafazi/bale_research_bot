import requests
from bs4 import BeautifulSoup
import re
import urllib3

# غیرفعال کردن هشدارهای مربوط به خطای SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def clean_doi(text):
    match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)', text)
    if match:
        return match.group(1)
    return text.strip()

def process_crossref_items(items):
    results = []
    for item in items:
        title = item.get('title', ['بدون عنوان'])[0]
        doi = item.get('DOI', 'No DOI')
        url = item.get('URL', '')
        publisher = item.get('publisher', 'ناشر نامشخص')
        
        authors_list = item.get('author', [])
        authors = ", ".join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_list[:3]])
        if len(authors_list) > 3:
            authors += " et al."
                
        results.append({
            'title': title,
            'doi': doi,
            'authors': authors if authors else "نامشخص",
            'publisher': publisher,
            'url': url
        })
    return results

def search_article_by_name(query):
    url = f"https://api.crossref.org/works?query.title={query}&rows=5&select=DOI,title,author,URL,publisher"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        items = data.get('message', {}).get('items', [])
        return process_crossref_items(items)
    except Exception as e:
        print(f"Crossref Name Error: {e}")
        return []

def search_article_by_doi(doi_input):
    doi = clean_doi(doi_input)
    url = f"https://api.crossref.org/works/{doi}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            item = res.json().get('message', {})
            return process_crossref_items([item])
        else:
            return [{
                'title': 'عنوان نامشخص (آماده برای تلاش دانلود از سرور)',
                'doi': doi,
                'authors': 'نامشخص',
                'publisher': 'نامشخص',
                'url': f'https://doi.org/{doi}'
            }]
    except Exception as e:
        print(f"Crossref DOI Error: {e}")
        return [{
            'title': 'خطا در دریافت اطلاعات (آماده برای تلاش دانلود مستقیم)',
            'doi': doi,
            'authors': 'نامشخص',
            'publisher': 'نامشخص',
            'url': f'https://doi.org/{doi}'
        }]

def get_scihub_pdf_url(doi_input):
    doi = clean_doi(doi_input)
    # دامنه ای که باز میشود در اولویت اول قرار گرفت
    base_urls = [
        'https://sci-hub.ist/', 
        'https://sci-hub.se/', 
        'https://sci-hub.ru/', 
        'https://sci-hub.st/'
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    for base in base_urls:
        try:
            target_url = f"{base}{doi}"
            res = requests.get(target_url, headers=headers, timeout=15, verify=False)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                pdf_url = None
                
                pdf_tag = soup.find(id='pdf')
                if pdf_tag and pdf_tag.get('src'):
                    pdf_url = pdf_tag['src']
                
                if not pdf_url:
                    button_tag = soup.find('button', onclick=re.compile(r"location\.href"))
                    if button_tag:
                        match = re.search(r"location\.href='(.*?)'", button_tag['onclick'])
                        if match:
                            pdf_url = match.group(1)

                if pdf_url:
                    if pdf_url.startswith('//'):
                        return 'https:' + pdf_url
                    elif pdf_url.startswith('/'):
                        return base.rstrip('/') + pdf_url
                    return pdf_url
        except Exception as e:
            print(f"Sci-Hub Error on {base}: {e}")
            continue
    return None

def download_pdf(url, filename):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': '*/*'
        }
        res = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if res.status_code == 200 and len(res.content) > 10000:
            filepath = f"{filename}.pdf"
            with open(filepath, 'wb') as f:
                f.write(res.content)
            return filepath
    except Exception as e:
        print(f"Download Error: {e}")
    return None
