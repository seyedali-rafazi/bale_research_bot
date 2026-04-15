import asyncio
import qrcode
from telethon import TelegramClient

API_ID = 6
API_HASH = 'eb06d4abfb49dc3eeb1aeb98ae0f581e'
SESSION_NAME = 'my_bale1_bot_session'

# همان پروکسی که کار کرد را اینجا می‌گذاریم
proxy_settings = ("socks5", '127.0.0.1', 10808) 

async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH, proxy=proxy_settings)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("⏳ در حال دریافت کد QR از تلگرام...")
        qr_login = await client.qr_login()
        
        # چاپ بارکد در کنسول
        qr = qrcode.QRCode(version=1, border=1)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        
        print("\n" + "="*50)
        print("1️⃣ تلگرام را روی گوشی خود باز کنید.")
        print("2️⃣ به Settings (تنظیمات) -> Devices (دستگاه‌ها) بروید.")
        print("3️⃣ روی Link Desktop Device (اتصال دستگاه جدید) بزنید.")
        print("4️⃣ بارکد بالا را با گوشی اسکن کنید.")
        print("="*50 + "\n")
        
        # منتظر می‌ماند تا شما بارکد را اسکن کنید
        await qr_login.wait()
        
    print("✅ با موفقیت لاگین شدید! فایل سشن ساخته شد.")
    await client.disconnect()

asyncio.run(main())
