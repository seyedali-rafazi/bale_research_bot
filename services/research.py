import os
import requests
from bs4 import BeautifulSoup
import re

# دریافت پروکسی از فایل env یا استفاده از مقدار پیش‌فرض شما
PROXY_URL = os.getenv('PROXY', 'socks5://127.0.0.1:40000')
PROXIES = {
    'http': PROXY_URL,
    'https': PROXY_URL
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

def clean_doi(doi_input):
    """پاک‌سازی و استخراج DOI خالص از لینک یا متن"""
    doi = doi_input.strip()
    doi = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', doi)
    return doi

def get_scihub_pdf_url(doi):
    """تلاش برای دریافت لینک PDF از سای‌هاب با استفاده از پروکسی"""
    scihub_urls = [
        'https://sci-hub.ist/', 
        'https://sci-hub.ru/'   
          ]
    
    for base in scihub_urls:
        try:
            target_url = f"{base}{doi}"
            # استفاده از پروکسی و غیرفعال کردن بررسی SSL
            res = requests.get(target_url, headers=HEADERS, proxies=PROXIES, timeout=15, verify=False)
            
            # بررسی اینکه صفحه کپچا/ربات نباشد
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
    """تلاش جایگزین برای دریافت لینک از Libgen"""
    try:
        search_url = f"http://libgen.rs/scimag/?q={doi}"
        res = requests.get(search_url, headers=HEADERS, proxies=PROXIES, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # پیدا کردن لینک‌های دانلود در جدول
            links = soup.find_all('a', href=True)
            for link in links:
                if 'scimag/ads.php?doi=' in link['href']:
                    download_page_url = link['href']
                    if not download_page_url.startswith('http'):
                        download_page_url = f"http://libgen.rs{download_page_url}"
                    
                    # رفتن به صفحه دانلود
                    res_dl = requests.get(download_page_url, headers=HEADERS, proxies=PROXIES, timeout=15)
                    soup_dl = BeautifulSoup(res_dl.text, 'html.parser')
                    
                    # پیدا کردن لینک نهایی PDF (معمولا در تگ a با متن GET یا لینک مستقیم)
                    main_link = soup_dl.find('a', string='GET')
                    if main_link and main_link.get('href'):
                        return main_link.get('href')
    except Exception as e:
        print(f"Libgen Error: {e}")
        
    return None

def get_article_download_url(doi_input):
    """تابع اصلی که ابتدا سای‌هاب و سپس لیب‌جن را چک می‌کند"""
    doi = clean_doi(doi_input)
    
    # 1. اول تلاش از طریق سای هاب
    pdf_url = get_scihub_pdf_url(doi)
    if pdf_url:
        return pdf_url
        
    # 2. اگر سای هاب جواب نداد یا کپچا داد، تلاش از طریق لیب جن
    print("Sci-Hub failed or returned captcha. Trying Libgen...")
    pdf_url = get_libgen_pdf_url(doi)
    
    return pdf_url
