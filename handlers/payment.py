from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes
import datetime
# ایمپورت کردن تابع جدید ثبت تراکنش به همراه تابع تنظیم VIP
from core.database import set_vip_with_expiration, add_transaction 
from dotenv import load_dotenv
import os

# بارگذاری متغیرهای محیطی
load_dotenv() 
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")
PAYMENT_VALUE = os.getenv("PAYMENT_VALUE")

async def btn_buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    title = "اشتراک VIP"
    description = "ارتقا به حساب ویژه برای یک ماه"
    payload = f"vip_1month_{chat_id}"
    currency = "IRR" 
    prices = [LabeledPrice("اشتراک 1 ماهه", PAYMENT_VALUE)] 

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=PROVIDER_TOKEN,
        currency=currency,
        prices=prices,
        start_parameter="buy_vip"
    )

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("vip_1month_"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="خطا در اطلاعات پرداخت.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    payment_info = update.message.successful_payment
    
    # 1. استخراج اطلاعات پرداخت
    total_amount = payment_info.total_amount # مبلغ به ریال
    payload = payment_info.invoice_payload
    provider_charge_id = payment_info.provider_payment_charge_id # کد پیگیری درگاه
    
    # 2. ثبت تراکنش در دیتابیس (سیستم لاگ)
    add_transaction(
        user_id=chat_id,
        amount=total_amount,
        payload=payload,
        provider_charge_id=provider_charge_id
    )
    
    # 3. ارتقا کاربر به VIP به مدت ۳۰ روز
    expiration_date = datetime.datetime.now() + datetime.timedelta(days=30)
    set_vip_with_expiration(chat_id, 1, expiration_date) 
    
    # 4. ایجاد و ارسال رسید پرداخت برای کاربر
    amount_toman = int(total_amount / 10) # محاسبه تومان: $ amount / 10 $
    receipt_text = (
        "✅ **پرداخت شما با موفقیت تایید و ثبت شد!**\n\n"
        "🧾 **رسید تراکنش شما:**\n"
        f"👤 شناسه: `{chat_id}`\n"
        f"💰 مبلغ: {amount_toman:,} تومان\n"
        f"🔖 کد پیگیری درگاه: `{provider_charge_id}`\n\n"
        "🌟 شما اکنون کاربر VIP هستید و محدودیت‌های شما تا یک ماه آینده برداشته شد."
    )
    
    await update.message.reply_text(text=receipt_text, parse_mode='Markdown')
