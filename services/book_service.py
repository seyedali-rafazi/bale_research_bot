import io
import requests
from bs4 import BeautifulSoup
import urllib.parse

def search_books_by_name(query: str, limit: int = 5):
    """
    جستجوی واقعی کتاب در سایت LibGen
    """
    url = f"http://libgen.is/search.php?req={urllib.parse.quote(query)}&res=25&view=simple&phrase=1&column=def"
    books = []
    
    try:
        # هدر برای اینکه سایت ما را ربات تشخیص ندهد
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # پیدا کردن جدول نتایج
            table = soup.find('table', class_='c')
            if not table:
                return []
                
            rows = table.find_all('tr')[1:] # ردیف اول هدر است
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 10:
                    ext = cols[8].text.strip().lower()
                    if ext != 'pdf': # فعلا فقط pdf ها را جدا میکنیم
                        continue
                        
                    author = cols[1].text.strip()
                    # استخراج عنوان و لینک MD5
                    title_col = cols[2]
                    title_a = title_col.find_all('a')
                    title = title_a[0].text.strip() if title_a else "نامشخص"
                    
                    year = cols[4].text.strip()
                    
                    # پیدا کردن لینک دانلود (MD5)
                    md5_link = ""
                    mirrors = cols[9].find_all('a')
                    if mirrors:
                        md5_link = mirrors[0].get('href', '')

                    books.append({
                        'title': title,
                        'author': author[:50],
                        'year': year,
                        'link': md5_link # لینک صفحه دانلود
                    })
                    
                    if len(books) >= limit:
                        break
    except Exception as e:
        print(f"Error scraping LibGen: {e}")
        
    return books

async def download_book_pdf(book_data: dict) -> io.BytesIO:
    """
    دریافت فایل واقعی PDF از لینک LibGen
    """
    try:
        download_page_url = book_data.get('link')
        if not download_page_url:
            return None

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        # 1. ورود به صفحه دانلود (library.lol) برای استخراج لینک مستقیم
        page_resp = requests.get(download_page_url, headers=headers, timeout=15)
        if page_resp.status_code != 200:
            return None
            
        soup = BeautifulSoup(page_resp.text, 'html.parser')
        download_link_tag = soup.find('a', string='GET') or soup.select_one('#download h2 a')
        
        if not download_link_tag:
            return None
            
        direct_link = download_link_tag.get('href')
        
        # 2. دانلود فایل PDF
        pdf_resp = requests.get(direct_link, headers=headers, timeout=60, stream=True)
        if pdf_resp.status_code == 200:
            # بررسی حجم فایل (تلگرام اجازه ارسال فایل بیشتر از 50 مگابایت را به ربات‌های معمولی نمی‌دهد)
            content_length = pdf_resp.headers.get('content-length')
            if content_length and int(content_length) > 50 * 1024 * 1024:
                print("حجم فایل بیشتر از 50 مگابایت است.")
                return None
                
            file_stream = io.BytesIO(pdf_resp.content)
            safe_title = "".join(x for x in book_data['title'] if x.isalnum() or x in " _-")
            file_stream.name = f"{safe_title[:30]}.pdf"
            
            return file_stream
            
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        
    return None
