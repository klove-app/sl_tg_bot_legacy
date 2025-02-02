from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from database.logger import logger
from config.config import DATABASE_URL

# Проверяем URL подключения
print(f"DATABASE_URL from config: {DATABASE_URL}")  # Временно для отладки
print(f"Environment DATABASE_URL: {os.getenv('DATABASE_URL')}")  # Временно для отладки
print(f"Environment DATABASE_PUBLIC_URL: {os.getenv('DATABASE_PUBLIC_URL')}")  # Временно для отладки

# Создаем URL для подключения к базе данных
SQLALCHEMY_DATABASE_URL = os.getenv('DATABASE_PUBLIC_URL', DATABASE_URL)
print(f"Using SQLALCHEMY_DATABASE_URL: {SQLALCHEMY_DATABASE_URL}")  # Временно для отладки

# Создаем движок базы данных
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=True,  # Включаем логирование SQL
    echo_pool=True  # Включаем логирование пула соединений
)

# Добавляем обработчики событий для отладки
@event.listens_for(engine, 'before_cursor_execute')
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    logger.debug(f"Executing SQL: {statement}")
    logger.debug(f"Parameters: {parameters}")

@event.listens_for(engine, 'connect')
def receive_connect(dbapi_connection, connection_record):
    logger.info("New database connection established")

@event.listens_for(engine, 'checkout')
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")

@event.listens_for(engine, 'checkin')
def receive_checkin(dbapi_connection, connection_record):
    logger.debug("Database connection returned to pool")

logger.info("PostgreSQL database engine created with connection pool")

# Создаем фабрику сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Предотвращаем истечение объектов после коммита
)
logger.info("Session factory created")

# Создаем базовый класс для моделей
Base = declarative_base()
logger.info("Base model class created")

def get_db():
    """Генератор сессий базы данных"""
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        logger.debug("Yielding database session")
        yield db
    except Exception as e:
        logger.error(f"Error in database session: {e}")
        raise
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
        # Проверяем подключение
        with engine.connect() as connection:
            logger.info("Testing database connection...")
            result = connection.execute("SELECT 1")
            logger.info(f"Connection test result: {result.scalar()}")
            
            # Проверяем текущую базу данных
            result = connection.execute("SELECT current_database()")
            logger.info(f"Current database: {result.scalar()}")
            
            # Проверяем таблицы
            result = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in result]
            logger.info(f"Available tables: {tables}")
        
        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise 