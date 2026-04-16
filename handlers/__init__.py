# handlers/__init__.py

import re
from telegram.ext import MessageHandler, CommandHandler, PreCheckoutQueryHandler, filters
from core.constants import *
from .commands import cmd_start
from .menus import (btn_back_action, btn_article_menu, btn_search_doi_req, 
                    btn_search_name_req, btn_user_info, btn_support_req, btn_citation_req) # اضافه شد
from .states import process_state_input 
from core.admin import cmd_stats, cmd_setvip
from .payment import btn_buy_vip, precheckout_callback, successful_payment_callback

def register_all_handlers(application):
    application.add_handler(CommandHandler('stats', cmd_stats))
    application.add_handler(CommandHandler('setvip', cmd_setvip))
    application.add_handler(CommandHandler('start', cmd_start))

    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BACK)}$"), btn_back_action))

    # هندلرهای پرداخت
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BUY_VIP)}$"), btn_buy_vip))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    # منو مقالات و رفرنس (جدید)
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_ARTICLE)}$"), btn_article_menu))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SEARCH_DOI)}$"), btn_search_doi_req))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SEARCH_NAME)}$"), btn_search_name_req))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_CITATION)}$"), btn_citation_req)) # ثبت هندلر جدید
    
    # منوی کاربران و پشتیبانی
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_USER_INFO)}$"), btn_user_info))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SUPPORT)}$"), btn_support_req))

    # پردازش متون ارسالی کاربر بر اساس وضعیت
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_state_input))
