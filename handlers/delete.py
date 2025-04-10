"""Модуль содержит обработчики для удаления."""
from datetime import datetime, date
from models import (
    session_scope,
    IncomeRecord,
    ExpenseRecord,
    IncomeCategory,
    ExpenseCategory
)
from telebot import types
import calendar
from typing import Dict, Any


class DeleteHandler:
    """Обработчик удаления записей (транзакций/доходов) через Telegram-бота."""

    def __init__(self, bot, send_welcome_func):
        """Инициализация обработчика удаления записей."""
        self.bot = bot
        self.send_welcome = send_welcome_func
        self.current_record_type = None
        self.user_records = {}
        self.date_selection_state: Dict[int, Dict[str, Any]] = {}
        self.register_handlers()

    def show_records(self, message, date_from, date_to=None):
        """Показать записи за дату или период для удаления в виде кнопок."""
        def format_amount(amount):
            """Форматирует сумму для отображения без научной нотации."""
            try:
                is_integer = (
                    isinstance(amount, float) and amount.is_integer()
                )
                if isinstance(amount, int) or is_integer:
                    return str(int(amount))
                if abs(amount) > 1e16:
                    return "{0:.0f}".format(amount)
                return str(amount)
            except Exception:
                return str(amount)

        user_id = message.chat.id
        model = (
            IncomeRecord
            if self.current_record_type == "income"
            else ExpenseRecord
        )
        with session_scope() as session:
            query = session.query(model).filter(model.user_id == user_id)

            if date_to:
                query = query.filter(model.date.between(date_from, date_to))
                date_text = (
                    f"с {date_from.strftime('%d.%m.%Y')} "
                    f"по {date_to.strftime('%d.%m.%Y')}"
                )
            else:
                query = query.filter(model.date == date_from)
                date_text = f"за {date_from.strftime('%d.%m.%Y')}"

            records = query.order_by(model.date).all()

            if not records:
                self.bot.send_message(
                    user_id,
                    f"Нет записей {'доходов' if self.current_record_type == 'income' else 'расходов'} {date_text}",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return self.send_welcome(message)

            self.user_records[user_id] = [
                {
                    'id': r.id,
                    'date': r.date.strftime('%d.%m.%Y'),
                    'category': r.category,
                    'amount': r.amount
                }
                for r in records
            ]

            markup = types.ReplyKeyboardMarkup(
                resize_keyboard=True,
                row_width=1
            )

            for i, record in enumerate(self.user_records[user_id], 1):
                formatted_amount = format_amount(record['amount'])
                btn_text = f"{i}. {record['date']} - {record['category']}: {formatted_amount} руб."
                markup.add(types.KeyboardButton(btn_text))

            markup.add(types.KeyboardButton("Отмена"))

            self.bot.send_message(
                user_id,
                f"📋 Выберите запись для удаления {date_text}:",
                reply_markup=markup
            )

            self.bot.register_next_step_handler(
                message,
                self.process_deletion,
                user_id
            )

    def register_handlers(self):
        """Регистрация всех обработчиков команд."""

        @self.bot.message_handler(func=lambda m: m.text == "Удалить запись 🗑️")
        def delete_menu(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Очистить все данные", "Удалить конкретную запись")
            markup.add("Назад")
            self.bot.send_message(
                message.chat.id,
                "Выберите действие:",
                reply_markup=markup
            )

        @self.bot.message_handler(
            func=lambda m: m.text == "Очистить все данные"
        )
        def confirm_clear_all(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Подтвердить удаление", "Отмена")
            self.bot.send_message(
                message.chat.id,
                "⚠️ Вы уверены что хотите удалить ВСЕ данные? Это нельзя отменить!",
                reply_markup=markup
            )

        @self.bot.message_handler(
            func=lambda m: m.text == "Подтвердить удаление"
        )
        def clear_all_data(message):
            user_id = message.chat.id
            with session_scope() as session:
                session.query(IncomeRecord).filter_by(user_id=user_id).delete()
                session.query(ExpenseRecord).filter_by(user_id=user_id).delete()
                session.query(IncomeCategory).filter_by(user_id=user_id).delete()
                session.query(ExpenseCategory).filter_by(user_id=user_id).delete()

            self.bot.send_message(
                user_id,
                "✅ Все данные и категории успешно удалены",
                reply_markup=types.ReplyKeyboardRemove()
            )
            self.send_welcome(message)

        @self.bot.message_handler(
            func=lambda m: m.text == "Удалить конкретную запись"
        )
        def select_record_type(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Доход", "Расход")
            markup.add("Назад")
            self.bot.send_message(
                message.chat.id,
                "Выберите тип записи для удаления:",
                reply_markup=markup
            )

        @self.bot.message_handler(func=lambda m: m.text in ["Доход", "Расход"])
        def set_record_type(message):
            self.current_record_type = "income" if message.text == "Доход" else "expense"
            self.show_year_selection(message, is_period=True)

        @self.bot.message_handler(func=lambda m: m.text == "Назад")
        def handle_back(message):
            self.send_welcome(message)



        @self.bot.message_handler(func=lambda m: m.text == "Отмена")
        def handle_cancel(message):
            if message.chat.id in self.date_selection_state:
                del self.date_selection_state[message.chat.id]
            self.bot.send_message(
                message.chat.id,
                "Действие отменено",
                reply_markup=types.ReplyKeyboardRemove()
            )
            self.send_welcome(message)

    def show_year_selection(self, message, is_period: bool):
        """Показать выбор года."""
        user_id = message.chat.id
        current_year = datetime.now().year

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)

        years = list(range(2000, current_year + 2))
        for i in range(0, len(years), 4):
            row = [types.KeyboardButton(str(year)) for year in years[i:i+4]]
            markup.add(*row)

        markup.add(types.KeyboardButton("Отмена"))

        if user_id not in self.date_selection_state:
            self.date_selection_state[user_id] = {
                "is_period": is_period,
                "step": "start_year" if is_period else "year"
            }

        state = self.date_selection_state[user_id]

        if state.get("step") == "end_year":
            text = "Выберите конечный год:"
        else:
            text = "Выберите начальный год:" if is_period else "Выберите год:"

        msg = self.bot.send_message(user_id, text, reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.process_year_selection)

    def show_month_selection(self, message, year: int, prefix: str):
        """Показать выбор месяца."""
        user_id = message.chat.id
        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)

        for i in range(0, 12, 3):
            row = [types.KeyboardButton(month) for month in months_ru[i:i+3]]
            markup.add(*row)

        markup.add(types.KeyboardButton("Отмена"))

        text = f"Выберите {prefix} месяц:" if prefix else "Выберите месяц:"
        msg = self.bot.send_message(user_id, text, reply_markup=markup)
        self.bot.register_next_step_handler(
            msg,
            self.process_month_selection,
            year
        )

    def process_month_selection(self, message, year: int):
        """Обработка выбора месяца."""
        user_id = message.chat.id

        if message.text == "Отмена":
            if user_id in self.date_selection_state:
                del self.date_selection_state[user_id]
            return self.send_welcome(message)

        months_ru = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]

        try:
            month = months_ru.index(message.text) + 1
        except ValueError:
            msg = self.bot.send_message(
                user_id,
                "❌ Пожалуйста, выберите месяц из предложенных вариантов"
            )
            return self.bot.register_next_step_handler(
                msg,
                self.process_month_selection,
                year
            )

        state = self.date_selection_state.get(user_id)
        if not state:
            return self.send_welcome(message)

        state["month"] = month

        if state["is_period"]:
            if state["step"] == "start_month":
                state["step"] = "start_day"
                self.show_day_selection(message, year, month, "начальный")
            elif state["step"] == "end_month":
                state["step"] = "end_day"
                self.show_day_selection(message, year, month, "конечный")
        else:
            state["step"] = "day"
            self.show_day_selection(message, year, month, "")

    def show_day_selection(self, message, year: int, month: int, prefix: str):
        """Показать выбор дня."""
        user_id = message.chat.id
        _, last_day = calendar.monthrange(year, month)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=7)

        days = list(range(1, last_day + 1))
        for i in range(0, len(days), 7):
            row = [types.KeyboardButton(str(day)) for day in days[i:i+7]]
            markup.add(*row)

        markup.add(types.KeyboardButton("Отмена"))

        month_name = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ][month - 1]

        text = f"Выберите {prefix} день {month_name} {year} года:" if prefix else f"Выберите день {month_name} {year} года:"
        msg = self.bot.send_message(user_id, text, reply_markup=markup)
        self.bot.register_next_step_handler(
            msg,
            self.process_day_selection,
            year,
            month
        )

    def process_year_selection(self, message):
        """Обработка выбора года."""
        user_id = message.chat.id

        if message.text == "Отмена":
            if user_id in self.date_selection_state:
                del self.date_selection_state[user_id]
            return self.send_welcome(message)

        try:
            year = int(message.text)
            current_year = datetime.now().year
            if year < 2000 or year > current_year + 1:
                raise ValueError
        except ValueError:
            msg = self.bot.send_message(
                user_id,
                "❌ Пожалуйста, выберите год из предложенных вариантов"
            )
            return self.bot.register_next_step_handler(
                msg,
                self.process_year_selection
            )

        state = self.date_selection_state.get(user_id)
        if not state:
            return self.send_welcome(message)

        state["year"] = year

        if state["is_period"]:
            if state["step"] == "start_year":
                state["step"] = "start_month"
                self.show_month_selection(message, year, "начальный")
            elif state["step"] == "end_year":
                state["step"] = "end_month"
                self.show_month_selection(message, year, "конечный")
        else:
            state["step"] = "month"
            self.show_month_selection(message, year, "")

    def process_day_selection(self, message, year: int, month: int):
        """Обработка выбора дня."""
        user_id = message.chat.id

        if message.text == "Отмена":
            if user_id in self.date_selection_state:
                del self.date_selection_state[user_id]
            return self.send_welcome(message)

        try:
            day = int(message.text)
            _, last_day = calendar.monthrange(year, month)
            if day < 1 or day > last_day:
                raise ValueError
        except ValueError:
            msg = self.bot.send_message(
                user_id,
                "❌ Пожалуйста, выберите день из предложенных вариантов"
            )
            return self.bot.register_next_step_handler(
                msg,
                self.process_day_selection,
                year,
                month
            )

        state = self.date_selection_state.get(user_id)
        if not state:
            return self.send_welcome(message)

        selected_date = date(year, month, day)

        if state["is_period"]:
            if state["step"] == "start_day":
                state["start_date"] = selected_date
                state["step"] = "end_year"

                self.date_selection_state[user_id] = state

                msg = self.bot.send_message(
                    user_id,
                    "Теперь выберите конечную дату",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                self.show_year_selection(msg, is_period=True)
            elif state["step"] == "end_day":
                end_date = selected_date
                start_date = state["start_date"]

                if end_date < start_date:
                    self.bot.send_message(
                        user_id,
                        "❌ Конечная дата должна быть позже начальной. Начните заново."
                    )
                    if user_id in self.date_selection_state:
                        del self.date_selection_state[user_id]
                    return self.send_welcome(message)

                if user_id in self.date_selection_state:
                    del self.date_selection_state[user_id]
                self.show_records(message, start_date, end_date)
        else:
            if user_id in self.date_selection_state:
                del self.date_selection_state[user_id]
            self.show_records(message, selected_date)

    def process_deletion(self, message, user_id):
        """Обработка выбора записи для удаления."""
        if message.text.lower() == "отмена":
            return self.send_welcome(message)

        try:
            num_str = message.text.split('.')[0]
            num = int(num_str.strip())

            if 1 <= num <= len(self.user_records.get(user_id, [])):
                record_id = self.user_records[user_id][num-1]['id']
                self.confirm_deletion(message, record_id)
            else:
                raise ValueError
        except (ValueError, IndexError):
            try:
                self.bot.send_message(
                    user_id,
                    "❌ Неверный номер, попробуйте еще раз"
                )
                self.bot.register_next_step_handler(
                    message,
                    self.process_deletion,
                    user_id
                )
            except Exception as e:
                print(f"Ошибка при обработке удаления: {e}")
                self.send_welcome(message)

    def confirm_deletion(self, message, record_id):
        """Подтверждение удаления записи."""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Удалить", "Отмена")

        try:
            sent_msg = self.bot.send_message(
                message.chat.id,
                "Вы точно хотите удалить эту запись?",
                reply_markup=markup
            )

            # Сохраняем информацию о текущем удалении
            self.current_deletion = {
                'user_id': message.chat.id,
                'record_id': record_id,
                'message_id': sent_msg.message_id
            }

            self.bot.register_next_step_handler(
                sent_msg,
                self.handle_deletion_confirmation
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
            self.send_welcome(message)

    def handle_deletion_confirmation(self, message):
        """Обработка подтверждения удаления."""
        if not hasattr(self, 'current_deletion'):
            return self.send_welcome(message)

        try:
            # Проверяем, что ответ соответствует одному из предложенных вариантов
            if message.text not in ["Удалить", "Отмена"]:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add("Удалить", "Отмена")

                # Удаляем предыдущее сообщение с кнопками
                try:
                    self.bot.delete_message(
                        message.chat.id,
                        message.message_id - 1
                    )
                except Exception as e:
                    print(f"Не удалось удалить сообщение: {e}")

                msg = self.bot.send_message(
                    message.chat.id,
                    "❌ Пожалуйста, выберите один из предложенных вариантов:",
                    reply_markup=markup
                )

                self.bot.register_next_step_handler(
                    msg,
                    self.handle_deletion_confirmation
                )
                return

            if message.text == "Отмена":
                self.bot.send_message(
                    message.chat.id,
                    "Удаление отменено",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return self.send_welcome(message)

            if message.text == "Удалить":
                model = IncomeRecord if self.current_record_type == "income" else ExpenseRecord
                with session_scope() as session:
                    session.query(model).filter_by(
                        id=self.current_deletion['record_id']
                    ).delete()

                self.bot.send_message(
                    message.chat.id,
                    "✅ Запись успешно удалена",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return self.send_welcome(message)

        except Exception as e:
            print(f"Ошибка при обработке подтверждения: {e}")
            try:
                self.bot.send_message(
                    message.chat.id,
                    "⚠️ Произошла ошибка при удалении",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            except Exception:
                pass
            return self.send_welcome(message)
        finally:
            if hasattr(self, 'current_deletion'):
                del self.current_deletion

        @self.bot.message_handler(
            func=lambda m: m.text in ["Удалить", "Отмена"]
        )
        def handle_confirmation(m):
            if not hasattr(self, 'current_deletion'):
                return self.send_welcome(m)

            record_id = self.current_deletion['record_id']

            if m.text == "Отмена":
                self.bot.send_message(
                    m.chat.id,
                    "Удаление отменено",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return self.send_welcome(m)

            model = IncomeRecord if self.current_record_type == "income" else ExpenseRecord
            with session_scope() as session:
                session.query(model).filter_by(id=record_id).delete()

            self.bot.send_message(
                m.chat.id,
                "✅ Запись успешно удалена",
                reply_markup=types.ReplyKeyboardRemove()
            )
            self.send_welcome(m)


def register_delete_handlers(bot, send_welcome_func):
    """Инициализация обработчиков удаления."""
    DeleteHandler(bot, send_welcome_func)
