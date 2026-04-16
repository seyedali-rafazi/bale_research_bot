# handlers/__init__.py

import re
from telegram.ext import MessageHandler, CommandHandler, filters
from core.constants import *
from .commands import cmd_start
from .menus import (btn_back_action, btn_article_menu, btn_search_doi_req, 
                    btn_search_name_req, btn_user_info, btn_support_req)
from .states import process_state_input 
from core.admin import cmd_stats, cmd_setvip

def register_all_handlers(application):
    application.add_handler(CommandHandler('stats', cmd_stats))
    application.add_handler(CommandHandler('setvip', cmd_setvip))
    application.add_handler(CommandHandler('start', cmd_start))

    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_BACK)}$"), btn_back_action))
    
    # منو مقالات
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_ARTICLE)}$"), btn_article_menu))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SEARCH_DOI)}$"), btn_search_doi_req))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SEARCH_NAME)}$"), btn_search_name_req))
    
    # منوی کاربران و پشتیبانی
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_USER_INFO)}$"), btn_user_info))
    application.add_handler(MessageHandler(filters.Regex(f"^{re.escape(BTN_SUPPORT)}$"), btn_support_req))

    # پردازش متون ارسالی کاربر بر اساس وضعیت
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_state_input))
