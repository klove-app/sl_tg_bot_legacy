from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from database.logger import logger
from config.config import DATABASE_NAME, DATABASE_URL

# Получаем путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), DATABASE_NAME)
logger.info(f"Database path: {DB_PATH}")

# Создаем URL для подключения к базе данных
SQLALCHEMY_DATABASE_URL = DATABASE_URL
logger.info(f"Database URL: {SQLALCHEMY_DATABASE_URL}")

# Создаем движок базы данных с пулом соединений
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800
)
logger.info("Database engine created")

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
    logger.info("Initializing database")
    try:
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise 