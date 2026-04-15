# core/keyboards.py 

from telegram import ReplyKeyboardMarkup, KeyboardButton
from .constants import *

def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton(BTN_ARTICLE)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_article_menu_keyboard():
    keyboard = [
        [KeyboardButton(BTN_SEARCH_DOI)],
        [KeyboardButton(BTN_SEARCH_NAME)],
        [KeyboardButton(BTN_BACK)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)