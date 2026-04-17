# core/keyboards.py

from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from .constants import *


def get_main_menu_keyboard():
    keyboard = [
        [KeyboardButton(BTN_ARTICLE)],
        [KeyboardButton(BTN_BOOK_SEARCH)],
        [KeyboardButton(BTN_SMART_ABSTRACT), KeyboardButton(BTN_CITATION)],
        [KeyboardButton(BTN_TRANSLATE), KeyboardButton(BTN_BIBTEX)],
        [KeyboardButton(BTN_USER_INFO), KeyboardButton(BTN_SUPPORT)],
        [KeyboardButton(BTN_BUY_VIP)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_article_menu_keyboard():
    keyboard = [
        [KeyboardButton(BTN_SEARCH_DOI)],
        [KeyboardButton(BTN_SEARCH_NAME)],
        [KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_citation_format_keyboard():
    keyboard = [
        [KeyboardButton(BTN_APA), KeyboardButton(BTN_IEEE)],
        [KeyboardButton(BTN_HARVARD)],
        [KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# کیبورد جدید برای انتخاب سال
def get_year_filter_keyboard():
    keyboard = [
        [KeyboardButton(BTN_YEAR_ALL)],
        [KeyboardButton(BTN_YEAR_2015), KeyboardButton(BTN_YEAR_2020)],
        [KeyboardButton(BTN_YEAR_2024)],
        [KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_sort_filter_keyboard():
    keyboard = [
        [KeyboardButton(BTN_SORT_RELEVANCE)],
        [KeyboardButton(BTN_SORT_CITATION)],
        [KeyboardButton(BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_books_inline_keyboard(books_count: int):
    keyboard = []
    row = []
    for i in range(books_count):
        # دکمه ها با نام 📥 1, 📥 2 و ...
        row.append(InlineKeyboardButton(f"📥 {i + 1}", callback_data=f"dlbook_{i}"))
        if len(row) == 4:  # هر ردیف ۴ دکمه
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)