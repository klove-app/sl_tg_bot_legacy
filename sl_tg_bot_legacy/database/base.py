from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from database.logger import logger
from config.config import DATABASE_URL

# Создаем URL для подключения к базе данных
SQLALCHEMY_DATABASE_URL = DATABASE_URL
logger.info(f"Connecting to PostgreSQL database")

# Создаем движок базы данных
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=True  # Включаем логирование SQL
)
logger.info("PostgreSQL database engine created with connection pool")

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("Session factory created")

# Создаем базовый класс для моделей
Base = declarative_base()
logger.info("Base model class created")

def get_db():
    """Генератор сессий базы данных"""
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()

# Создаем глобальную сессию для использования в моделях
Session = sessionmaker(bind=engine)
logger.info("Global session created")

def init_db():
    """Инициализация базы данных"""
    logger.info("Initializing PostgreSQL database")
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise 