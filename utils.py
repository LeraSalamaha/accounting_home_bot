"""Модуль для работы с клавиатурой Telegram бота."""

from telebot import types


def main_menu_button():
    """Создает кнопку для возврата в главное меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в главное меню"))
    return markup
