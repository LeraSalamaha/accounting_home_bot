
"""
Модуль для работы с базой данных с использованием SQLAlchemy.

Содержит определения моделей и функции для взаимодействия с базой данных.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager


DATABASE_URL = 'sqlite:///finance_bot.db'
Base = declarative_base()


class IncomeCategory(Base):
    """Представляет категорию дохода для пользователя."""

    __tablename__ = 'income_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    name = Column(String, unique=True)


class ExpenseCategory(Base):
    """Представляет категорию расхода для пользователя."""

    __tablename__ = 'expense_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    name = Column(String, unique=True)


class IncomeRecord(Base):
    """Представляет запись о доходе пользователя."""

    __tablename__ = 'income_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    category = Column(String)
    amount = Column(Float)
    date = Column(Date, nullable=False)


class ExpenseRecord(Base):
    """Представляет запись о расходе пользователя."""

    __tablename__ = 'expense_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    category = Column(String)
    amount = Column(Float)
    date = Column(Date, nullable=False)


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)


Session = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """Управляет сессией базы данных с автоматическим откатом и закрытием."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_income_categories(user_id, session):
    """Возвращает все категории доходов для указанного пользователя."""
    return session.query(IncomeCategory).filter_by(user_id=user_id).all()


def get_expense_categories(user_id, session):
    """Возвращает все категории расходов для указанного пользователя."""
    return session.query(ExpenseCategory).filter_by(user_id=user_id).all()
