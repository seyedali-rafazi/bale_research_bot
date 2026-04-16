# handlers/payment.py
from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
import datetime
from core.database import set_vip_with_expiration # این تابع را باید در دیتابیس خود بسازید

PROVIDER_TOKEN = "WALLET-TEST-1111111111111111" # توکن کیف پول شما

async def btn_buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    title = "اشتراک یک ماهه VIP"
    description = "با خرید این اشتراک به مدت ۳۰ روز محدودیت دانلود شما افزایش می‌یابد."
    payload = f"vip_1month_{chat_id}"
    currency = "IRR" # ریال
    # قیمت ۵۰ هزار تومان معادل ۵۰۰,۰۰۰ ریال است
    prices = [LabeledPrice("اشتراک 1 ماهه", 200000)]

    await context.bot.send_invoice(
        chat_id, title, description, payload, PROVIDER_TOKEN, currency, prices
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید اولیه قبل از کسر موجودی"""
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("vip_1month_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="خطا در اطلاعات پرداخت.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عملیات بعد از پرداخت موفق"""
    chat_id = str(update.effective_chat.id)
    payment_info = update.message.successful_payment
    
    # اضافه کردن 30 روز به تاریخ فعلی
    expiration_date = datetime.datetime.now() + datetime.timedelta(days=30)
    
    # شما باید تابع زیر را در دیتابیس خود اضافه کنید تا تاریخ انقضا را هم ذخیره کند
    set_vip_with_expiration(chat_id, 1, expiration_date) 
    
    await update.message.reply_text("✅ پرداخت شما با موفقیت انجام شد!\nشما اکنون کاربر VIP هستید و محدودیت‌های شما تا یک ماه آینده برداشته شد. 🌟")
