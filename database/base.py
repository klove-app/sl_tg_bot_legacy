from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config.config import DATABASE_NAME

# Создаем URL для подключения к SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_NAME}"

# Создаем движок базы данных
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Только для SQLite
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей
Base = declarative_base()

def get_db():
    """Функция-генератор для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

# Создаем глобальную сессию для использования в моделях
Session = SessionLocal 