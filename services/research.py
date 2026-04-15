import os
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# تنظیمات پروکسی
# ==========================================
PROXY_URL = os.getenv('PROXY', 'socks5://127.0.0.1:40000')
PROXIES = {
    'http': PROXY_URL,
    'https': PROXY_URL
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# ==========================================
# بخش اول: جستجوی مقالات (Crossref)
# ==========================================

def format_crossref_item(item):
    """فرمت کردن دیتای خام کراس‌رف به شکل قابل خواندن برای ربات"""
    # استخراج عنوان
    title = item.get('title', ['بدون عنوان'])[0]
    
    # استخراج نویسندگان و تبدیل لیست به یک رشته متنی
    authors_raw = item.get('author', [])
    authors_list = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors_raw]
    authors = ", ".join(filter(None, authors_list))
    if not authors:
        authors = "نامشخص"
        
    return {
        'title': title,
        'authors': authors,
        'publisher': item.get('publisher', 'نامشخص'),
        'doi': item.get('DOI', 'ندارد'),
        'url': item.get('URL', 'ندارد')
    }

def search_article_by_name(query):
    """جستجوی مقاله بر اساس نام از طریق API رایگان Crossref"""
    try:
        url = f"https://api.crossref.org/works?query.title={query}&select=DOI,title,author,publisher,URL&rows=5"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            items = data.get('message', {}).get('items', [])
            return [format_crossref_item(item) for item in items]
    except Exception as e:
        print(f"Crossref Name Search Error: {e}")
    return []

def search_article_by_doi(doi):
    """جستجوی مقاله بر اساس DOI از طریق API رایگان Crossref"""
    doi_clean = clean_doi(doi)
    try:
        url = f"https://api.crossref.org/works/{doi_clean}"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            item = data.get('message', {})
            if item:
                return [format_crossref_item(item)]
    except Exception as e:
        print(f"Crossref DOI Search Error: {e}")
    return []

# ==========================================
# بخش دوم: استخراج لینک دانلود (Sci-Hub و Libgen)
# ==========================================

def clean_doi(doi_input):
    """پاکسازی لینک‌های اضافی و استخراج شناسه خالص DOI"""
    if not doi_input:
        return ""
    doi = doi_input.strip()
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi)
    return doi

def get_scihub_pdf_url(doi):
    """تلاش برای پیدا کردن لینک PDF از سایت سای‌هاب"""
    scihub_urls = ['https://sci-hub.ist/', 'https://sci-hub.ru/', 'https://sci-hub.se/']
    for base in scihub_urls:
        try:
            target_url = f"{base}{doi}"
            res = requests.get(target_url, headers=HEADERS, proxies=PROXIES, timeout=15, verify=False)
            
            if res.status_code == 200 and "проверка на робота" not in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                pdf_url = None
                
                embed_tag = soup.find('embed')
                if embed_tag:
                    pdf_url = embed_tag.get('src') or embed_tag.get('original-url')
                
                if not pdf_url:
                    iframe_tag = soup.find('iframe', id='pdf')
                    if iframe_tag:
                        pdf_url = iframe_tag.get('src')

                if pdf_url:
                    pdf_url = pdf_url.split('#')[0]
                    if pdf_url.startswith('//'):
                        return 'https:' + pdf_url
                    elif pdf_url.startswith('/'):
                        return base.rstrip('/') + pdf_url
                    elif not pdf_url.startswith('http'):
                        return base.rstrip('/') + '/' + pdf_url
                    return pdf_url
        except Exception as e:
            print(f"Sci-Hub Error on {base}: {e}")
            continue
    return None

def get_libgen_pdf_url(doi):
    """تلاش برای پیدا کردن لینک PDF از سایت لیب‌جن"""
    try:
        search_url = f"http://libgen.rs/scimag/?q={doi}"
        res = requests.get(search_url, headers=HEADERS, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                if 'scimag/ads.php?doi=' in link['href']:
                    download_page_url = link['href']
                    if not download_page_url.startswith('http'):
                        download_page_url = f"http://libgen.rs{download_page_url}"
                    
                    res_dl = requests.get(download_page_url, headers=HEADERS, proxies=PROXIES, timeout=15)
                    soup_dl = BeautifulSoup(res_dl.text, 'html.parser')
                    main_link = soup_dl.find('a', string='GET')
                    if main_link and main_link.get('href'):
                        return main_link.get('href')
    except Exception as e:
        print(f"Libgen Error: {e}")
    return None

def download_pdf(doi_input):
    """تابع اصلی که تلگرام برای دریافت لینک دانلود صدا می‌زند"""
    doi = clean_doi(doi_input)
    if not doi:
        return None
        
    # 1. اول تلاش از طریق سای هاب
    pdf_url = get_scihub_pdf_url(doi)
    if pdf_url:
        return pdf_url
        
    # 2. اگر سای هاب جواب نداد تلاش از طریق لیب جن
    print("Sci-Hub failed. Trying Libgen...")
    pdf_url = get_libgen_pdf_url(doi)
    
    return pdf_url
