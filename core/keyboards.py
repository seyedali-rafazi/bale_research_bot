# core/keyboards.py 

from telegram import ReplyKeyboardMarkup, KeyboardButton
from .constants import *

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton(BTN_ARTICLE)],
        [ KeyboardButton(BTN_CITATION)],
        [KeyboardButton(BTN_USER_INFO), KeyboardButton(BTN_SUPPORT)],
        [KeyboardButton(BTN_BUY_VIP)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_article_menu_keyboard():
    keyboard = [
        [KeyboardButton(BTN_SEARCH_DOI)],
        [KeyboardButton(BTN_SEARCH_NAME)],
        [KeyboardButton(BTN_BACK)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# کیبورد جدید برای انتخاب فرمت رفرنس
def get_citation_format_keyboard():
    keyboard = [
        [KeyboardButton(BTN_APA), KeyboardButton(BTN_IEEE)],
        [KeyboardButton(BTN_HARVARD)],
        [KeyboardButton(BTN_BACK)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
