import asyncio
import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = 6
API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"
SESSION_NAME = "research-session"
proxy_settings = ("socks5", "127.0.0.1", 10808)


async def login_with_qr(client):
    while True:
        print("⏳ در حال ساخت QR جدید...")
        qr_login = await client.qr_login()

        qr = qrcode.QRCode(version=1, border=1)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)

        print("\n" + "=" * 50)
        print("1️⃣ تلگرام را روی گوشی خود باز کنید.")
        print("2️⃣ به Settings -> Devices بروید.")
        print("3️⃣ روی Link Desktop Device بزنید.")
        print("4️⃣ همین الان QR را اسکن کنید.")
        print("=" * 50 + "\n")

        try:
            await qr_login.wait(timeout=60)
            return True

        except asyncio.TimeoutError:
            print("⌛ زمان QR تمام شد یا اسکن انجام نشد. QR جدید ساخته می‌شود...\n")
            continue

        except SessionPasswordNeededError:
            password = input("🔐 رمز Two-Step Verification را وارد کنید: ")
            await client.sign_in(password=password)
            return True


async def main():
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH, proxy=proxy_settings)
    await client.connect()

    if not await client.is_user_authorized():
        await login_with_qr(client)

    print("✅ با موفقیت لاگین شدید! فایل سشن ساخته شد.")
    await client.disconnect()


asyncio.run(main())
