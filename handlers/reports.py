"""Модуль содержит обработчики для отчетов."""

from datetime import datetime, timedelta
from telebot import types
from telebot.types import Message, CallbackQuery
from sqlalchemy import func
from models import (
    session_scope,
    IncomeRecord,
    ExpenseRecord,
    get_income_categories,
    get_expense_categories,
    IncomeCategory,
    ExpenseCategory
)
DATE_SELECTION_START = 1
DATE_SELECTION_END = 2

date_selection_state = {}


def register_report_handlers(bot):
    """Регистрирует обработчики сообщений для отчетов."""

    def format_large_number(num):
        """Форматирует большие числа в читаемый вид без научной нотации."""
        if num is None:
            return "0"
        try:
            num = float(num)
            # Для очень больших чисел
            if abs(num) > 1e16:
                return "{0:,.0f}".format(num).replace(",", " ")
            # Для обычных чисел
            if num.is_integer():
                return "{0:,.0f}".format(num).replace(",", " ")
            return "{0:,.2f}".format(num).replace(",", " ")
        except Exception:
            return str(num)

    @bot.message_handler(func=lambda message: message.text == "Отчеты 📊")
    def report_menu(message: Message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Отчет по деньгам")
        item2 = types.KeyboardButton("Отчет по категориям")
        item3 = types.KeyboardButton("Общий отчет")
        markup.add(item1, item2, item3)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))
        bot.send_message(
            message.chat.id,
            "Выберите тип отчета:",
            reply_markup=markup
        )

    @bot.message_handler(
        func=lambda message: message.text == "Отчет по деньгам"
    )
    def month_report_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Выбрать период")
        item2 = types.KeyboardButton("За текущий месяц")
        markup.add(item1, item2)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))
        bot.send_message(
            message.chat.id,
            "Выберите опцию:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "Выбрать период")
    def ask_date_range_for_money_report(message):
        now = datetime.now()
        markup = generate_calendar(
            now.year,
            now.month,
            DATE_SELECTION_START,
            "money"
        )
        bot.send_message(
            message.chat.id,
            "Выберите начальную дату:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "Выбрать месяц")
    def ask_month_for_month_report(message):
        now = datetime.now()
        markup = generate_calendar(now.year, now.month, None, "month")
        bot.send_message(
            message.chat.id,
            "Выберите месяц:",
            reply_markup=markup
        )

    # Общие функции для работы с календарем
    def generate_calendar(year, month, selection_type=None, report_type=None):
        markup = types.InlineKeyboardMarkup()

        months = [
            "Январь",
            "Февраль",
            "Март",
            "Апрель",
            "Май",
            "Июнь",
            "Июль",
            "Август",
            "Сентябрь",
            "Октябрь",
            "Ноябрь",
            "Декабрь"
        ]
        markup.row(
            types.InlineKeyboardButton(
                f"{months[month-1]} {year}",
                callback_data="ignore"
            )
        )

        markup.row(
            *[types.InlineKeyboardButton(day, callback_data="ignore")
              for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]]
        )

        first_day = datetime(year, month, 1)
        starting_day = first_day.weekday()

        if month == 12:
            next_month = 1
            next_year = year + 1
        else:
            next_month = month + 1
            next_year = year

        last_day = datetime(next_year, next_month, 1) - timedelta(days=1)
        days_in_month = last_day.day

        days = []
        days.extend([" " for _ in range(starting_day)])

        for day in range(1, days_in_month + 1):
            days.append(str(day))

        for i in range(0, len(days), 7):
            row = days[i:i+7]
            buttons = []
            for day in row:
                if day == " ":
                    buttons.append(
                        types.InlineKeyboardButton(" ", callback_data="ignore")
                    )
                else:
                    callback_data = f"report_{year}-{month:02d}-{int(day):02d}"
                    if selection_type:
                        callback_data += f"_{selection_type}"
                    if report_type:
                        callback_data += f"_{report_type}"
                    buttons.append(
                        types.InlineKeyboardButton(
                            day,
                            callback_data=callback_data
                        )
                    )
            markup.row(*buttons)

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        nav_buttons = []
        if selection_type and report_type:
            nav_buttons.append(
                types.InlineKeyboardButton(
                    "<",
                    callback_data=f"nav_{prev_year}_{prev_month}_{selection_type}_{report_type}"
                )
            )
            nav_buttons.append(
                types.InlineKeyboardButton(
                    ">",
                    callback_data=f"nav_{next_year}_{next_month}_{selection_type}_{report_type}"
                )
            )
        else:
            nav_buttons.append(
                types.InlineKeyboardButton("<", callback_data=f"nav_{prev_year}_{prev_month}")
            )
            nav_buttons.append(
                types.InlineKeyboardButton(">", callback_data=f"nav_{next_year}_{next_month}")
            )

        markup.row(*nav_buttons)

        return markup

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('report_')
    )
    def handle_date_selection(call: CallbackQuery):
        parts = call.data.split('_')
        date_str = parts[1]

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")

            if len(parts) >= 3:
                selection_type = int(parts[2]) if parts[2].isdigit() else None
                report_type = parts[3] if len(parts) >= 4 else None

                if selection_type == DATE_SELECTION_START:
                    date_selection_state[call.message.chat.id] = {
                        'start_date': date,
                        'selection_type': DATE_SELECTION_END,
                        'report_type': report_type
                    }
                    bot.edit_message_text(
                        "Теперь выберите конечную дату:",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=generate_calendar(
                            date.year,
                            date.month,
                            DATE_SELECTION_END,
                            report_type
                        )
                    )
                elif selection_type == DATE_SELECTION_END:
                    state = date_selection_state.get(call.message.chat.id)
                    if state and 'start_date' in state:
                        start_date = state['start_date']
                        end_date = date

                        # Проверка что конечная дата не меньше начальной
                        if end_date < start_date:
                            bot.answer_callback_query(
                                call.id,
                                "Конечная дата не может быть раньше начальной!",
                                show_alert=True
                            )
                            return

                        if report_type == "month":
                            generate_month_report_from_calendar(
                                call.message,
                                date
                            )
                        elif report_type == "category":
                            generate_category_report_from_dates(
                                call.message,
                                start_date,
                                end_date
                            )
                        elif report_type == "overall":
                            generate_overall_report_from_dates(
                                call.message,
                                start_date,
                                end_date
                            )
                        elif report_type == "money":
                            generate_money_report_from_dates(
                                call.message,
                                start_date,
                                end_date
                            )

                        if call.message.chat.id in date_selection_state:
                            del date_selection_state[call.message.chat.id]
                else:
                    if report_type == "month":
                        generate_month_report_from_calendar(call.message, date)
            else:
                generate_month_report_from_calendar(call.message, date)

        except ValueError:
            bot.answer_callback_query(call.id, "Неверный формат даты")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('nav_'))
    def handle_navigation(call: CallbackQuery):
        parts = call.data.split('_')
        year = int(parts[1])
        month = int(parts[2])

        if len(parts) >= 4:
            selection_type = int(parts[3]) if parts[3].isdigit() else None
            report_type = parts[4] if len(parts) >= 5 else None
            markup = generate_calendar(
                year,
                month,
                selection_type,
                report_type
            )
        else:
            markup = generate_calendar(year, month)

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('change_month_')
    )
    def handle_month_change(call: CallbackQuery):
        _, _, year, month = call.data.split('_')
        year = int(year)
        month = int(month)
        markup = generate_calendar(year, month)
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )

    def generate_money_report_from_dates(message, start_date, end_date):
        user_id = message.chat.id

        # Преобразуем даты в объекты date (без времени)
        start_date = start_date.date() if isinstance(start_date, datetime) else start_date
        end_date = end_date.date() if isinstance(end_date, datetime) else end_date

        with session_scope() as session:
            # Запросы используют только даты (без времени)
            total_income = session.query(func.sum(IncomeRecord.amount)).filter(
                IncomeRecord.user_id == user_id,
                func.date(IncomeRecord.date) >= start_date,
                func.date(IncomeRecord.date) <= end_date
            ).scalar() or 0

            total_expense = session.query(func.sum(ExpenseRecord.amount)).filter(
                ExpenseRecord.user_id == user_id,
                func.date(ExpenseRecord.date) >= start_date,
                func.date(ExpenseRecord.date) <= end_date
            ).scalar() or 0

            remaining_funds = total_income - total_expense

            report_text = (
                f"Отчет за период с {start_date} по {end_date}:\n"
                f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
                f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
                f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n"
            )

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    def generate_month_report_from_calendar(message, date):
        user_id = message.chat.id
        start_date = date.replace(day=1)
        if date.month == 12:
            end_date = date.replace(year=date.year+1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = date.replace(month=date.month+1, day=1) - timedelta(days=1)

        with session_scope() as session:
            total_income = session.query(func.sum(IncomeRecord.amount)).filter(
                IncomeRecord.user_id == user_id,
                func.date(IncomeRecord.date) >= start_date.date(),
                func.date(IncomeRecord.date) <= end_date.date()
            ).scalar() or 0

            total_expense = session.query(func.sum(ExpenseRecord.amount)).filter(
                ExpenseRecord.user_id == user_id,
                func.date(ExpenseRecord.date) >= start_date.date(),
                func.date(ExpenseRecord.date) <= end_date.date()
            ).scalar() or 0

            remaining_funds = total_income - total_expense

            report_text = (
                f"Отчет за {date.month}/{date.year}:\n"
                f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
                f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
                f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n"
            )

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    def generate_month_report(message):
        try:
            date = datetime.strptime(message.text, "%Y-%m-%d")
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, введите дату "
                "в формате 'YYYY-MM-DD'."
            )
            month_report_menu(message)
            return

        user_id = message.chat.id
        month = date.month
        year = date.year

        with session_scope() as session:
            total_income = session.query(func.sum(IncomeRecord.amount)).filter(
                IncomeRecord.user_id == user_id,
                func.extract('year', IncomeRecord.date) == year,
                func.extract('month', IncomeRecord.date) == month
            ).scalar() or 0

            total_expense = session.query(
                func.sum(ExpenseRecord.amount)
            ).filter(
                ExpenseRecord.user_id == user_id,
                func.extract('year', ExpenseRecord.date) == year,
                func.extract('month', ExpenseRecord.date) == month
            ).scalar() or 0

            remaining_funds = total_income - total_expense

            report_text = (
                f"Отчет за {month}/{year}:\n"
                f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
                f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
                f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n"
            )

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    @bot.message_handler(
        func=lambda message: message.text == "За текущий месяц"
    )
    def generate_current_month_report(message):
        now = datetime.now()
        month = now.month
        year = now.year
        user_id = message.chat.id

        with session_scope() as session:


            total_income = session.query(func.sum(IncomeRecord.amount)).filter(
                IncomeRecord.user_id == user_id,
                func.extract('year', IncomeRecord.date) == year,
                func.extract('month', IncomeRecord.date) == month
            ).scalar() or 0

            total_expense = session.query(
                func.sum(ExpenseRecord.amount)
            ).filter(
                ExpenseRecord.user_id == user_id,
                func.extract('year', ExpenseRecord.date) == year,
                func.extract('month', ExpenseRecord.date) == month
            ).scalar() or 0


            remaining_funds = total_income - total_expense

            report_text = (
                f"Отчет за {month}/{year}:\n"
                f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
                f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
                f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n"
            )

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    # Обработчики для отчетов по категориям
    @bot.message_handler(
        func=lambda message: message.text == "Отчет по категориям"
    )
    def category_report_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Выбрать период для отчета по категориям")
        item2 = types.KeyboardButton("За текущий месяц по категориям")
        markup.add(item1, item2)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))
        bot.send_message(
            message.chat.id,
            "Выберите опцию:",
            reply_markup=markup
        )

    @bot.message_handler(
        func=lambda message: message.text == "Выбрать период для отчета по категориям"
    )
    def ask_date_range_for_category_report(message):
        now = datetime.now()
        markup = generate_calendar(
            now.year,
            now.month,
            DATE_SELECTION_START,
            "category"
        )
        bot.send_message(
            message.chat.id,
            "Выберите начальную дату:",
            reply_markup=markup
        )

    @bot.message_handler(
            func=lambda message: message.text ==
            "Ввести даты для отчета по категориям"
        )
    def ask_date_range(message):
        bot.send_message(
            message.chat.id,
            "Введите начальную дату в формате 'YYYY-MM-DD':"
        )
        bot.register_next_step_handler(message, process_start_date_category)

    def process_start_date_category(message):
        try:
            start_date = datetime.strptime(message.text, "%Y-%m-%d")
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, введите дату "
                "в формате 'YYYY-MM-DD'."
            )
            ask_date_range(message)
            return

        bot.send_message(
            message.chat.id,
            "Введите конечную дату в формате 'YYYY-MM-DD':"
        )
        bot.register_next_step_handler(
            message,
            lambda msg: check_end_date_category(msg, start_date)
        )

    def check_end_date_category(message, start_date):
        try:
            end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
            start_date = start_date.date()

            if end_date < start_date:
                bot.send_message(
                    message.chat.id,
                    "Конечная дата не может быть раньше начальной. "
                    "Пожалуйста, введите корректную конечную дату:"
                )
                bot.register_next_step_handler(
                    message,
                    lambda msg: check_end_date_category(msg, start_date)
                )
                return

            generate_category_report(message, start_date)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, попробуйте снова."
            )
            bot.register_next_step_handler(
                message,
                lambda msg: check_end_date_category(msg, start_date)
            )

    def generate_category_report_from_dates(message, start_date, end_date):
        user_id = message.chat.id

        # Преобразуем даты в объекты date (без времени)
        start_date = start_date.date() if isinstance(start_date, datetime) else start_date
        end_date = end_date.date() if isinstance(end_date, datetime) else end_date

        with session_scope() as session:
            income_categories = [
                cat.name
                for cat in session.query(IncomeCategory)
                .filter_by(user_id=user_id)
                .all()
            ]
            expense_categories = [
                cat.name
                for cat in session.query(ExpenseCategory)
                .filter_by(user_id=user_id)
                .all()
            ]

            income_summary = {category: 0 for category in income_categories}
            expense_summary = {category: 0 for category in expense_categories}

            income_records = session.query(IncomeRecord).filter(
                IncomeRecord.user_id == user_id,
                func.date(IncomeRecord.date) >= start_date,
                func.date(IncomeRecord.date) <= end_date
            ).all()

            expense_records = session.query(ExpenseRecord).filter(
                ExpenseRecord.user_id == user_id,
                func.date(ExpenseRecord.date) >= start_date,
                func.date(ExpenseRecord.date) <= end_date
            ).all()

            for record in income_records:
                if record.category not in income_summary:
                    income_summary[record.category] = 0
                income_summary[record.category] += record.amount

            for record in expense_records:
                if record.category not in expense_summary:
                    expense_summary[record.category] = 0
                expense_summary[record.category] += record.amount

        report_text = (
            f"Отчет по категориям с {start_date} по {end_date}:\n\n"
            "Доходы:\n"
        )
        for category, total in income_summary.items():
            report_text += f"{category}: {format_large_number(total)} 💵\n"

        report_text += "\nРасходы:\n"
        for category, total in expense_summary.items():
            report_text += f"{category}: {format_large_number(total)} 💸\n"

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    def generate_category_report(message, start_date):
        try:
            end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, попробуйте снова."
            )
            return

        user_id = message.chat.id

        with session_scope() as session:
            income_categories = [
                cat.name
                for cat in session.query(IncomeCategory)
                .filter_by(user_id=user_id)
                .all()
            ]
            expense_categories = [
                cat.name
                for cat in session.query(ExpenseCategory)
                .filter_by(user_id=user_id)
                .all()
            ]

            income_summary = {category: 0 for category in income_categories}
            expense_summary = {category: 0 for category in expense_categories}

            start_date = start_date.date()

            income_records = session.query(IncomeRecord).filter(
                IncomeRecord.user_id == user_id,
                IncomeRecord.date >= start_date,
                IncomeRecord.date <= end_date
            ).all()

            expense_records = session.query(ExpenseRecord).filter(
                ExpenseRecord.user_id == user_id,
                ExpenseRecord.date >= start_date,
                ExpenseRecord.date <= end_date
            ).all()

            for record in income_records:
                if record.category not in income_summary:
                    income_summary[record.category] = 0
                income_summary[record.category] += record.amount

            for record in expense_records:
                if record.category not in expense_summary:
                    expense_summary[record.category] = 0
                expense_summary[record.category] += record.amount

        report_text = (
            f"Отчет по категориям с {start_date} по {end_date}:\n\n"
            "Доходы:\n"
        )
        for category, total in income_summary.items():
            report_text += f"{category}: {format_large_number(total)} 💵\n"

        report_text += "\nРасходы:\n"
        for category, total in expense_summary.items():
            report_text += f"{category}: {format_large_number(total)} 💸\n"

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    @bot.message_handler(
            func=lambda message: message.text ==
            "За текущий месяц по категориям"
        )
    def generate_current_month_category_report(message):
        now = datetime.now()
        month = now.month
        year = now.year
        user_id = message.chat.id

        with session_scope() as session:
            income_records = session.query(IncomeRecord).filter(
                IncomeRecord.user_id == user_id,
                func.extract('year', IncomeRecord.date) == year,
                func.extract('month', IncomeRecord.date) == month
            ).all()

            expense_records = session.query(ExpenseRecord).filter(
                ExpenseRecord.user_id == user_id,
                func.extract('year', ExpenseRecord.date) == year,
                func.extract('month', ExpenseRecord.date) == month
            ).all()

            income_categories = [
                cat.name
                for cat in session.query(IncomeCategory)
                .filter_by(user_id=user_id)
                .all()
            ]
            expense_categories = [
                cat.name
                for cat in session.query(ExpenseCategory)
                .filter_by(user_id=user_id)
                .all()
            ]

            income_summary = {category: 0 for category in income_categories}
            expense_summary = {category: 0 for category in expense_categories}

            for record in income_records:
                if record.category not in income_summary:
                    income_summary[record.category] = 0
                income_summary[record.category] += record.amount

            for record in expense_records:
                if record.category not in expense_summary:
                    expense_summary[record.category] = 0
                expense_summary[record.category] += record.amount

        report_text = f"Отчет по категориям за {month}/{year}:\n\nДоходы:\n"
        for category in income_categories:
            report_text += f"{category}: {format_large_number(income_summary.get(category, 0))} 💵\n"

        report_text += "\nРасходы:\n"
        for category in expense_categories:
            report_text += (
                f"{category}: {format_large_number(expense_summary.get(category, 0))} 💸\n"
            )

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    # Обработчики для общего отчета
    @bot.message_handler(func=lambda message: message.text == "Общий отчет")
    def overall_report_menu(message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item1 = types.KeyboardButton("Выбрать период для общего отчета")
        item2 = types.KeyboardButton("За текущий месяц для общего отчета")
        markup.add(item1, item2)
        markup.add(types.KeyboardButton("Вернуться в главное меню"))

        bot.send_message(
            message.chat.id,
            "Выберите опцию:",
            reply_markup=markup
        )

    @bot.message_handler(
        func=lambda message: message.text == "Выбрать период для общего отчета"
    )
    def ask_date_range_for_overall_report(message):
        now = datetime.now()
        markup = generate_calendar(
            now.year,
            now.month,
            DATE_SELECTION_START,
            "overall"
        )
        bot.send_message(
            message.chat.id,
            "Выберите начальную дату:",
            reply_markup=markup
        )

    def generate_overall_report_from_dates(message, start_date, end_date):
        user_id = message.chat.id

        # Преобразуем даты в объекты date (без времени)
        start_date = start_date.date() if isinstance(start_date, datetime) else start_date
        end_date = end_date.date() if isinstance(end_date, datetime) else end_date

        with session_scope() as session:
            total_income = session.query(func.sum(IncomeRecord.amount)).filter(
                IncomeRecord.user_id == user_id,
                func.date(IncomeRecord.date) >= start_date,
                func.date(IncomeRecord.date) <= end_date
            ).scalar() or 0

            total_expense = session.query(func.sum(ExpenseRecord.amount)).filter(
                ExpenseRecord.user_id == user_id,
                func.date(ExpenseRecord.date) >= start_date,
                func.date(ExpenseRecord.date) <= end_date
            ).scalar() or 0

            income_records = session.query(IncomeRecord).filter(
                IncomeRecord.user_id == user_id,
                func.date(IncomeRecord.date) >= start_date,
                func.date(IncomeRecord.date) <= end_date
            ).all()

            expense_records = session.query(ExpenseRecord).filter(
                ExpenseRecord.user_id == user_id,
                func.date(ExpenseRecord.date) >= start_date,
                func.date(ExpenseRecord.date) <= end_date
            ).all()

            remaining_funds = total_income - total_expense

            income_categories = [
                cat.name
                for cat in get_income_categories(user_id, session)
            ]
            expense_categories = [
                cat.name
                for cat in get_expense_categories(user_id, session)
            ]

            income_summary = {category: 0 for category in income_categories}
            expense_summary = {category: 0 for category in expense_categories}

            for record in income_records:
                income_summary[record.category] += record.amount

            for record in expense_records:
                expense_summary[record.category] += record.amount

        report_text = (
            f"Общий отчет с {start_date} по {end_date}:\n"
            f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
            f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
            f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n\n"
            "Доходы по категориям:\n"
        )

        for category, total in income_summary.items():
            report_text += f"{category}: {format_large_number(total)} 💵\n"

        report_text += "\nРасходы по категориям:\n"
        for category, total in expense_summary.items():
            report_text += f"{category}: {format_large_number(total)} 💸\n"

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    @bot.message_handler(
            func=lambda message: message.text ==
            "Ввести дату для общего отчета"
        )
    def overall_ask_date_range(message):
        bot.send_message(
            message.chat.id,
            "Введите начальную дату в формате 'YYYY-MM-DD':"
        )
        bot.register_next_step_handler(message, process_start_date_overall)

    def process_start_date_overall(message):
        try:
            start_date = datetime.strptime(message.text, "%Y-%m-%d")
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, введите дату "
                "в формате 'YYYY-MM-DD'."
            )
            overall_ask_date_range(message)
            return

        bot.send_message(
            message.chat.id,
            "Введите конечную дату в формате 'YYYY-MM-DD':"
        )
        bot.register_next_step_handler(
            message,
            lambda msg: check_end_date_overall(msg, start_date)
        )

    def check_end_date_overall(message, start_date):
        try:
            end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
            start_date = start_date.date()

            if end_date < start_date:
                bot.send_message(
                    message.chat.id,
                    "Конечная дата не может быть раньше начальной. "
                    "Пожалуйста, введите корректную конечную дату:"
                )
                bot.register_next_step_handler(
                    message,
                    lambda msg: check_end_date_overall(msg, start_date)
                )
                return

            generate_overall_report(message, start_date)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, попробуйте снова."
            )
            bot.register_next_step_handler(
                message,
                lambda msg: check_end_date_overall(msg, start_date)
            )

    def generate_overall_report(message, start_date):
        try:
            end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Неверный формат даты. Пожалуйста, попробуйте снова."
            )
            return

        user_id = message.chat.id

        with session_scope() as session:
            income_records = session.query(IncomeRecord).filter(
                IncomeRecord.user_id == user_id,
                IncomeRecord.date >= start_date,
                IncomeRecord.date <= end_date
            ).all()

            expense_records = session.query(ExpenseRecord).filter(
                ExpenseRecord.user_id == user_id,
                ExpenseRecord.date >= start_date,
                ExpenseRecord.date <= end_date
            ).all()

            total_income = sum(record.amount for record in income_records)
            total_expense = sum(record.amount for record in expense_records)
            remaining_funds = total_income - total_expense

            income_categories = [
                cat.name
                for cat in get_income_categories(user_id, session)
            ]
            expense_categories = [
                cat.name
                for cat in get_expense_categories(user_id, session)
            ]

            income_summary = {category: 0 for category in income_categories}
            expense_summary = {category: 0 for category in expense_categories}

            for record in income_records:
                income_summary[record.category] += record.amount

            for record in expense_records:
                expense_summary[record.category] += record.amount

        report_text = (
            f"Общий отчет с {start_date} по {end_date}:\n"
            f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
            f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
            f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n\n"
            "Доходы по категориям:\n"
        )

        for category, total in income_summary.items():
            report_text += f"{category}: {total} 💵\n"

        report_text += "\nРасходы по категориям:\n"
        for category, total in expense_summary.items():
            report_text += f"{category}: {total} 💸\n"

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    @bot.message_handler(
            func=lambda message: message.text ==
            "За текущий месяц для общего отчета"
        )
    def generate_current_month_report(message):
        now = datetime.now()
        month = now.month
        year = now.year
        user_id = message.chat.id

        with session_scope() as session:
            total_income = session.query(func.sum(IncomeRecord.amount)).filter(
                IncomeRecord.user_id == user_id,
                func.extract('year', IncomeRecord.date) == year,
                func.extract('month', IncomeRecord.date) == month
            ).scalar() or 0

            total_expense = session.query(
                func.sum(ExpenseRecord.amount)
            ).filter(
                ExpenseRecord.user_id == user_id,
                func.extract('year', ExpenseRecord.date) == year,
                func.extract('month', ExpenseRecord.date) == month
            ).scalar() or 0

            income_records = session.query(IncomeRecord).filter(
                IncomeRecord.user_id == user_id,
                func.extract('year', IncomeRecord.date) == year,
                func.extract('month', IncomeRecord.date) == month
            ).all()

            expense_records = session.query(ExpenseRecord).filter(
                ExpenseRecord.user_id == user_id,
                func.extract('year', ExpenseRecord.date) == year,
                func.extract('month', ExpenseRecord.date) == month
            ).all()

            remaining_funds = total_income - total_expense

            report_text = (
                f"Отчет за {month}/{year}:\n"
                f"Общая сумма доходов: {format_large_number(total_income)} 💵\n"
                f"Общая сумма расходов: {format_large_number(total_expense)} 💸\n"
                f"Оставшиеся средства: {format_large_number(remaining_funds)} 💰\n\n"
                "Доходы по категориям:\n"
            )

            income_categories = [
                cat.name
                for cat in session.query(IncomeCategory)
                .filter_by(user_id=user_id)
                .all()
            ]
            expense_categories = [
                cat.name
                for cat in session.query(ExpenseCategory)
                .filter_by(user_id=user_id)
                .all()
            ]

            income_summary = {category: 0 for category in income_categories}
            expense_summary = {category: 0 for category in expense_categories}

            for record in income_records:
                if record.category not in income_summary:
                    income_summary[record.category] = 0
                income_summary[record.category] += record.amount

            for record in expense_records:
                if record.category not in expense_summary:
                    expense_summary[record.category] = 0
                expense_summary[record.category] += record.amount

            for category, total in income_summary.items():
                report_text += f"{category}: {format_large_number(total)} 💵\n"

            report_text += "\nРасходы по категориям:\n"
            for category, total in expense_summary.items():
                report_text += f"{category}: {format_large_number(total)} 💸\n"

        bot.send_message(message.chat.id, report_text)
        report_menu(message)

    @bot.message_handler(func=lambda message: message.text == "Выбрать месяц")
    def ask_month_for_month_report(message):
        now = datetime.now()
        markup = generate_calendar(now.year, now.month, None, "month")
        bot.send_message(
            message.chat.id,
            "Выберите месяц:",
            reply_markup=markup
        )
