"""Модуль содержит обработчики для старта."""
from telebot import types
from telebot.types import Message


def main_menu_button():
    """Кнопка для возвращения в главное меню."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Вернуться в главное меню"))
    return markup


def register_start_handlers(bot):
    """Регистрирует обработчики сообщений для старта."""
    def send_welcome(message: Message):
        welcome_text = (
            "Главное меню бота💰\n\n"
            "Выберите действие:"
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Добавить траты 💳")
        item2 = types.KeyboardButton("Отчеты 📊")
        item3 = types.KeyboardButton("Удалить запись 🗑️")
        item4 = types.KeyboardButton("Помощь ❓")
        markup.add(item1, item2, item3, item4)
        bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

    @bot.message_handler(commands=['start'])
    def start_handler(message: Message):
        send_welcome(message)

    @bot.message_handler(
            func=lambda message: message.text == "Вернуться в главное меню"
        )
    def welcome_back_handler(message: Message):
        send_welcome(message)

    @bot.message_handler(func=lambda message: message.text == "Помощь ❓")
    def send_help(message: Message):
        help_text = """
    📌 <b>Инструкция по использованию бота</b>

    <u>Основные команды:</u>
    /start - Главное меню

    <u>Главное меню:</u>
    💳 <b>Добавить траты</b> - Внести доход или расход
    📊 <b>Отчеты</b> - Посмотреть статистику
    🗑️ <b>Удалить запись</b> - Удалить данные
    ❓ <b>Помощь</b> - Справка

    <u>Как добавить доход/расход?</u>
    1. Нажмите <b>«Добавить траты»</b>
    2. Выберите <b>«Доходы»</b> или <b>«Расходы»</b>
    3. Создайте категорию или выберите существующую
    4. Укажите дату в календаре
    5. Введите сумму (например: 1500 или 2000.50)

    ⚠️ <i>Важно:</i>
    - Категории <b>не должны содержать маты</b>
    - Сумма - <b>только цифры и точка(запятые)</b>

    <u>Как посмотреть отчет?</u>
    1. Нажмите <b>«Отчеты»</b>
    2. Выберите тип:
    - <b>По деньгам</b> - общие суммы
    - <b>По категориям</b> - детализация
    - <b>Общий</b> - всё вместе
    3. Укажите период или выберите <b>«Текущий месяц»</b>

    <u>Как удалить запись?</u>
    1. Нажмите <b>«Удалить запись»</b>
    2. Выберите:
    - <b>Конкретную запись</b> → укажите дату и подтвердите
    - <b>Очистить всё</b> → удалит <b>все данные</b> (нельзя отменить!)

    <u>Частые вопросы:</u>
    ❔ <i>Как исправить ошибку в записи?</i>
    → Удалите неверную запись и создайте новую

    ❔ <i>Почему нет моих категорий?</i>
    → Сначала создайте их через <b>«Добавить траты» → «Создать категорию»</b>

    ❔ <i>Как посмотреть траты за прошлый месяц?</i>
    → В отчетах выберите <b>«Выбрать период»</b> и укажите даты

    🔄<b>Вернуться в главное меню:</b> Нажмите <i>«Вернуться в главное меню»</i>
    """
        bot.send_message(
            message.chat.id,
            help_text,
            parse_mode="HTML",
            reply_markup=main_menu_button()
        )

    return send_welcome
