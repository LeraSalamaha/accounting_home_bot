"""Основной модуль для запуска Telegram бота."""
from telebot import TeleBot
from telebot.types import Message
from handlers.start import register_start_handlers
from handlers.delete import register_delete_handlers
from handlers.reports import register_report_handlers
from handlers.transactions import register_transaction_handlers
import time
import threading
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = TeleBot(TOKEN)

# Настройки очистки сообщений
MAX_MESSAGES_IN_CHAT = 20
CLEANUP_INTERVAL = 60

# Словарь для хранения истории сообщений {chat_id: [message_ids]}
message_history = {}


def cleanup_old_messages():
    """Фоновая задача для очистки старых сообщений."""
    while True:
        try:
            for chat_id in list(message_history.keys()):
                if len(message_history[chat_id]) > MAX_MESSAGES_IN_CHAT:

                    messages_to_delete = message_history[chat_id][
                        :len(message_history[chat_id]) - MAX_MESSAGES_IN_CHAT
                    ]

                    for msg_id in messages_to_delete:
                        try:
                            bot.delete_message(chat_id, msg_id)
                            message_history[chat_id].remove(msg_id)
                        except Exception as e:
                            if "message to delete not found" in str(e).lower():
                                message_history[chat_id].remove(msg_id)
                            print(f"Ошибка удаления сообщения {msg_id}: {e}")

        except Exception as e:
            print(f"Ошибка в cleanup_old_messages: {e}")
        time.sleep(CLEANUP_INTERVAL)


# Запускаем очистку в фоновом режиме
cleanup_thread = threading.Thread(target=cleanup_old_messages, daemon=True)
cleanup_thread.start()


def track_message(func):
    """Декоратор для отслеживания отправленных сообщений."""
    def wrapped(*args, **kwargs):
        try:

            result = func(*args, **kwargs)

            if isinstance(result, Message):
                chat_id = result.chat.id
                msg_id = result.message_id

                if chat_id not in message_history:
                    message_history[chat_id] = []

                message_history[chat_id].append(msg_id)

            return result
        except Exception as e:
            print(f"Ошибка в track_message: {e}")
            raise

    return wrapped


# Применяем декоратор ко всем методам отправки сообщений
bot.send_message = track_message(bot.send_message)
bot.send_photo = track_message(bot.send_photo)
bot.send_document = track_message(bot.send_document)

# Регистрируем обработчики
send_welcome = register_start_handlers(bot)
register_report_handlers(bot)
register_transaction_handlers(bot)
register_delete_handlers(bot, send_welcome)

if __name__ == "__main__":
    bot.polling(none_stop=True)
