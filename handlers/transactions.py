"""Модуль содержит обработчики для доходов и расходов."""
from datetime import datetime, date
from telebot import types
from telebot.types import Message, CallbackQuery
from models import (
    session_scope,
    IncomeRecord,
    ExpenseRecord,
    IncomeCategory,
    ExpenseCategory
)


FORBIDDEN_WORDS = [
    'хуй', 'пизд', 'ебан', 'ебать', 'бля', 'блять', 'пидор', 'пидар', 'гандон',
    'мудак', 'сука', 'шлюха', 'долбоеб', 'залупа', 'гондон', 'педрик', 'чмо',
    'ебал', 'выеб', 'наеб', 'отъеб', 'подъеб', 'разъеб', 'съеб', 'уеб'
]

current_action = None
current_category = None
current_date = None
current_displayed_month = None
warning_shown = False

MONTH_NAMES = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}


def contains_profanity(text):
    """Проверяет текст на наличие ненормативной лексики."""
    text_lower = text.lower()
    replacements = {'*': '', '.': '', '-': '', '_': '', ' ': ''}
    cleaned_text = ''.join(replacements.get(c, c) for c in text_lower)

    for word in FORBIDDEN_WORDS:
        if word in cleaned_text:
            return True
    return False


def register_transaction_handlers(bot):
    """Регистрирует обработчики сообщений для отчетов и расходов."""
    @bot.message_handler(func=lambda message: message.text == "Добавить траты 💳")
    def add_expense_or_income(message: Message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Добавить доходы")
        item2 = types.KeyboardButton("Добавить расходы")
        markup.add(item1, item2)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))
        bot.send_message(
            message.chat.id,
            "Что вы хотите сделать?",
            reply_markup=markup
        )

    @bot.message_handler(
        func=lambda message: message.text == "Добавить доходы"
    )
    def add_income(message: Message):
        global current_action, warning_shown
        if not warning_shown:
            warning_text = (
                "⚠️ Внимание!\n"
                "Перед тем как у вас получится вернуться в главное меню\n"
                "Сначала нужно закончить действия по созданию записи\n\n"
                "ИЛИ\n\n"
                "Если вам нужно вернуться в главное меню,\n"
                "То нажмите на 'Вернуться в главное меню' ДВАЖДЫ \n"
            )
            bot.send_message(message.chat.id, warning_text)
            warning_shown = True
        current_action = "income"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Создать категорию")
        item2 = types.KeyboardButton("Использовать существующую категорию")
        markup.add(item1, item2)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=markup
        )

    @bot.message_handler(
        func=lambda message: message.text == "Добавить расходы"
    )
    def add_expense(message):
        global current_action, warning_shown
        if not warning_shown:
            warning_text = (
                "⚠️ Внимание!\n"
                "Перед тем как у вас получится вернуться в главное меню\n"
                "Сначала нужно закончить действия по созданию записи\n\n"
                "ИЛИ\n\n"
                "Если вам нужно вернуться в главное меню,\n"
                "То нажмите на 'Вернуться в главное меню' ДВАЖДЫ \n"
            )
            bot.send_message(message.chat.id, warning_text)
            warning_shown = True

        current_action = "expense"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Создать категорию")
        item2 = types.KeyboardButton("Использовать существующую категорию")
        markup.add(item1, item2)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=markup
        )

    @bot.message_handler(
        func=lambda message: message.text == "Создать категорию"
    )
    def create_category(message):

        bot.send_message(message.chat.id, "Введите название новой категории:")

        bot.register_next_step_handler(
            message,
            lambda msg: save_category(msg, message.chat.id)
        )

    def save_category(message, user_id):
        if message.text == "Вернуться в главное меню":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("Вернуться в главное меню"))
            return

        category_name = message.text

        # Проверка на ненормативную лексику
        if contains_profanity(category_name):
            bot.send_message(
                message.chat.id,
                "Название категории содержит недопустимые слова. Пожалуйста, придумайте другое название."
            )
            bot.register_next_step_handler(
                message,
                lambda msg: save_category(msg, user_id)
            )
            return

        with session_scope() as session:
            if current_action == "income":
                existing_categories = (
                    session.query(IncomeCategory)
                    .filter_by(user_id=user_id)
                    .all()
                )
            else:
                existing_categories = (
                    session.query(ExpenseCategory)
                    .filter_by(user_id=user_id)
                    .all()
                )

            if category_name not in [
                cat.name
                for cat in existing_categories if cat.user_id == user_id
            ]:
                if current_action == "income":
                    new_category = IncomeCategory(
                        user_id=user_id,
                        name=category_name
                    )
                    session.add(new_category)
                    bot.send_message(
                        message.chat.id,
                        f"Категория '{category_name}' для доходов "
                        "успешно создана!"
                    )
                else:
                    new_category = ExpenseCategory(
                        user_id=user_id,
                        name=category_name
                    )
                    session.add(new_category)
                    bot.send_message(
                        message.chat.id,
                        f"Категория '{category_name}' для расходов "
                        "успешно создана!"
                    )
            else:
                bot.send_message(
                    message.chat.id,
                    "Эта категория уже существует. "
                    "Пожалуйста, введите другое название."
                )

        if current_action == "income":
            add_income(message)
        else:
            add_expense(message)

    @bot.message_handler(
        func=lambda message: message.text == "Использовать существующую категорию"
    )
    def use_existing_category(message):
        user_id = message.chat.id

        if current_action == "income":
            with session_scope() as session:
                categories = (
                    session.query(IncomeCategory)
                    .filter_by(user_id=user_id)
                    .all()
                )
                if not categories:
                    bot.send_message(
                        message.chat.id,
                        "У вас нет созданных категорий для доходов."
                    )
                    add_income(message)
                    return
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for category in categories:
                    markup.add(types.KeyboardButton(category.name))
                markup.add(types.KeyboardButton("Вернуться в главное меню"))
                bot.send_message(
                    message.chat.id,
                    "Выберите категорию дохода:",
                    reply_markup=markup
                )
                bot.register_next_step_handler(
                    message,
                    process_category_selection
                )
        else:
            with session_scope() as session:
                categories = (
                    session.query(ExpenseCategory)
                    .filter_by(user_id=user_id)
                    .all()
                )
                if not categories:
                    bot.send_message(
                        message.chat.id,
                        "У вас нет созданных категорий для расходов."
                    )
                    add_expense(message)
                    return
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                for category in categories:
                    markup.add(types.KeyboardButton(category.name))
                markup.add(types.KeyboardButton("Вернуться в главное меню"))
                bot.send_message(
                    message.chat.id,
                    "Выберите категорию расхода:",
                    reply_markup=markup
                )
                bot.register_next_step_handler(
                    message,
                    process_category_selection
                )

    def process_category_selection(message):
        global current_category, current_displayed_month
        if message.text == "Вернуться в главное меню":
            return

        user_id = message.chat.id
        category_name = message.text

        # Проверяем существование категории в базе данных
        with session_scope() as session:
            if current_action == "income":
                category_exists = session.query(IncomeCategory).filter_by(
                    user_id=user_id,
                    name=category_name
                ).first()
            else:
                category_exists = session.query(ExpenseCategory).filter_by(
                    user_id=user_id,
                    name=category_name
                ).first()

        if not category_exists:
            bot.send_message(
                message.chat.id,
                f"Категория '{category_name}' не существует. Пожалуйста, выберите категорию из списка."
            )
            use_existing_category(message)
            return

        current_category = category_name
        current_displayed_month = datetime.now()
        show_calendar(message, current_displayed_month)

    def show_calendar(message, month_date):
        markup = types.InlineKeyboardMarkup()

        # Получаем русское название месяца
        month_name = MONTH_NAMES.get(
            month_date.month,
            month_date.strftime('%B')
        )

        markup.row(
            types.InlineKeyboardButton("<<", callback_data=f"calendar_prev_{month_date.year}_{month_date.month}"),
            types.InlineKeyboardButton(f"{month_name} {month_date.year}", callback_data="ignore"),
            types.InlineKeyboardButton(">>", callback_data=f"calendar_next_{month_date.year}_{month_date.month}")
        )

        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        markup.row(*[types.InlineKeyboardButton(day, callback_data="ignore") for day in week_days])

        if month_date.month == 12:
            next_month = month_date.replace(
                year=month_date.year+1,
                month=1,
                day=1
            )
        else:
            next_month = month_date.replace(month=month_date.month+1, day=1)
        days_in_month = (next_month - month_date.replace(day=1)).days

        first_day_weekday = month_date.replace(day=1).weekday()

        days = []
        for _ in range(first_day_weekday):
            days.append(types.InlineKeyboardButton(" ", callback_data="ignore"))

        for day in range(1, days_in_month + 1):
            days.append(
                types.InlineKeyboardButton(
                    str(day),
                    callback_data=f"calendar_day_{month_date.year}_{month_date.month}_{day}"
                )
            )

        for i in range(0, len(days), 7):
            markup.row(*days[i:i+7])

        bot.send_message(
            message.chat.id,
            "Выберите дату:",
            reply_markup=markup
        )

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('calendar_')
    )
    def handle_calendar_callback(call: CallbackQuery):
        global current_displayed_month

        try:
            if call.data.startswith("calendar_day_"):
                _, _, year, month, day = call.data.split("_")
                selected_date = date(int(year), int(month), int(day))
                global current_date
                current_date = selected_date

                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Выбрана дата: {selected_date.strftime('%Y-%m-%d')}\nВведите сумму:"
                )
                bot.register_next_step_handler(
                    call.message,
                    process_amount_input
                )

            elif call.data.startswith("calendar_prev_"):
                _, _, year, month = call.data.split("_")
                year, month = int(year), int(month)
                if month == 1:
                    year -= 1
                    month = 12
                else:
                    month -= 1
                current_displayed_month = date(year, month, 1)
                show_calendar(call.message, current_displayed_month)
                bot.answer_callback_query(call.id)

            elif call.data.startswith("calendar_next_"):
                _, _, year, month = call.data.split("_")
                year, month = int(year), int(month)
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1
                current_displayed_month = date(year, month, 1)
                show_calendar(call.message, current_displayed_month)
                bot.answer_callback_query(call.id)

        except Exception as e:
            print(f"Error in calendar callback: {e}")
            bot.answer_callback_query(
                call.id,
                "Произошла ошибка, попробуйте еще раз"
            )

    def process_amount_input(message):
        if message.text == "Вернуться в главное меню":
            return

        # Удаляем все пробелы из введенного текста
        cleaned_text = message.text.replace(' ', '')

        input_text = cleaned_text.replace(',', '.')
        if not input_text.replace('.', '').isdigit() or input_text.count('.') > 1:
            bot.send_message(
                message.chat.id,
                "Некорректный формат числа. Пожалуйста, введите число (например: 100 или 150.50)"
            )
            bot.register_next_step_handler(message, process_amount_input)
            return

        try:
            amount = float(input_text)

            if '.' in input_text:
                formatted_amount = input_text.rstrip('0').rstrip('.') if '.' in input_text else input_text
            else:
                formatted_amount = input_text

            if current_action == "income":
                record = IncomeRecord(
                    user_id=message.chat.id,
                    category=current_category,
                    amount=amount,
                    date=current_date
                )
                success_message = f"Запись о доходе {formatted_amount} для категории '{current_category}'"
            else:
                record = ExpenseRecord(
                    user_id=message.chat.id,
                    category=current_category,
                    amount=amount,
                    date=current_date
                )
                success_message = f"Запись о расходе {formatted_amount} для категории '{current_category}'"

            with session_scope() as session:
                session.add(record)

            bot.send_message(
                message.chat.id,
                f"{success_message} на дату '{current_date.strftime('%Y-%m-%d')}' успешно добавлена!"
            )

            if current_action == "income":
                add_income(message)
            else:
                add_expense(message)

        except ValueError:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, введите действительное число для суммы."
            )
            bot.register_next_step_handler(message, process_amount_input)
