# 📊 Финансовый бот для учета доходов и расходов

## 📌 Оглавление
1. [Функционал](#🔧-функционал)
2. [Архитектура](#🏗️-архитектура)
3. [Установка и запуск](#🚀-установка-и-запуск)
4. [Документация API](#📚-документация-api)
5. [Примеры использования](#💡-примеры-использования)
6. [Автор](#🧪-автор)


## 🔧 Функционал

### Основные возможности:
- **Учет операций**:
  - Добавление доходов/расходов
  - Категоризация операций
  - Гибкий выбор дат через календарь
- **Отчетность**:
  - Отчеты по периодам
  - Анализ по категориям
  - Общие сводки
- **Управление данными**:
  - Удаление отдельных записей
  - Полная очистка данных
  - Валидация вводимых значений

### Технические особенности:
```python
# Пример обработчика добавления операции
@bot.message_handler(func=lambda message: message.text == "Добавить траты")
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
```

## 🏗️ Архитектура

### Структура проекта:
```
finance-bot/
├── handlers/
│   ├── start.py       # Обработчики главного меню
│   ├── transactions.py # Логика операций
│   ├── reports.py     # Генерация отчетов
│   └── delete.py      # Удаление записей
├── models.py          # Модели данных
├── main.py            # Точка входа
└── README.md          # Документация
```

### Стек технологий:
- Python 3.9+
- Telebot (python-telegram-bot)
- SQLAlchemy (ORM)
- SQLite (база данных)

## 🚀 Установка и запуск

### Требования:
- Python 3.9 или новее
- Учетная запись Telegram бота

### Инструкция по установке:
1. Клонировать репозиторий:
```bash
git clone https://github.com/yourrepo/finance-bot.git
cd finance-bot
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Настроить бота:
```python
# В файле main.py
TOKEN = 'your_telegram_bot_token'
```

4. Запустить бота:
```bash
python main.py
```

## 📚 Документация API

### Модели данных:
```python
class IncomeRecord(Base):
    __tablename__ = 'income_records'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
```

### Основные обработчики:
| Метод | Описание | Параметры |
|-------|----------|-----------|
| `/start` | Инициализация бота | - |
| `add_expense_or_income` | Меню добавления операций | - |
| `generate_report` | Генерация отчетов | period_type |
| `delete_record` | Удаление записей | record_id |

## 💡 Примеры использования

### Пример работы с категориями:
```python
def save_category(message, user_id):
    if contains_profanity(message.text):
        bot.send_message("Недопустимое название категории")
        return
        
    with session_scope() as session:
        new_category = IncomeCategory(
            user_id=user_id,
            name=message.text
        )
        session.add(new_category)
```

### Пример валидации суммы:
```python
def process_amount_input(message):
    try:
        amount = float(message.text.replace(' ', '').replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message("Некорректная сумма")
```

## 🧪  Автор

Саламаха Валерия Юрьевна и Сорокин Никита Сергеевич 

связь с авторами в тг - @Lera_Salamaha , @Molo4niyLomtiK

бот - @accounting_home_bot

## PS.
просьба, если вдруг у вас не получится запустить бота, или он не будет вам отвечать , искренняя просьба связаться с нами.
мы приложим все возможные силы , чтоб ваша проверка была максимально комфортная и удачная 