import sqlite3
from datetime import datetime, date
from config.config import DATABASE_NAME
import logging

# Регистрируем адаптеры для корректной работы с датами в SQLite
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_adapter(date, lambda d: d.isoformat())

logger = logging.getLogger(__name__)

def get_connection():
    """Создает и возвращает соединение с базой данных"""
    return sqlite3.connect(DATABASE_NAME)

def update_existing_runs_chat_id():
    """Обновляет chat_id для существующих записей о пробежках"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Обновляем chat_id для всех NULL записей, добавляя префикс -100
        cursor.execute("""
            UPDATE running_log 
            SET chat_id = '-1001487049035'  -- Полный ID чата с префиксом
            WHERE chat_id IS NULL OR chat_id = '1487049035'
        """)
        
        affected_rows = cursor.rowcount
        conn.commit()
        logger.info(f"Chat_id успешно обновлен для {affected_rows} существующих записей")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении chat_id: {e}")
        conn.rollback()
    finally:
        conn.close()

def update_existing_runs_chat_type():
    """Обновляет chat_type для существующих записей о пробежках"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Обновляем chat_type для всех записей
        cursor.execute("""
            UPDATE running_log 
            SET chat_type = CASE
                WHEN chat_id IS NULL THEN 'private'
                ELSE 'group'
            END
            WHERE chat_type IS NULL
        """)
        
        affected_rows = cursor.rowcount
        conn.commit()
        logger.info(f"Chat_type успешно обновлен для {affected_rows} существующих записей")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении chat_type: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_missing_columns():
    """Добавляет недостающие колонки в таблицы"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Проверяем наличие колонки chat_type в таблице running_log
        cursor.execute("PRAGMA table_info(running_log)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем колонку chat_type в running_log, если её нет
        if 'chat_type' not in columns:
            cursor.execute('ALTER TABLE running_log ADD COLUMN chat_type TEXT')
            logger.info("Добавлена колонка chat_type в таблицу running_log")
            
            # После добавления колонки обновляем существующие записи
            update_existing_runs_chat_type()
        
        # Проверяем наличие колонки goal_km в таблице users
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем колонку goal_km в users, если её нет
        if 'goal_km' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN goal_km FLOAT DEFAULT 0')
            logger.info("Добавлена колонка goal_km в таблицу users")
            
        # Проверяем наличие колонки is_active в таблице users
        if 'is_active' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1')
            logger.info("Добавлена колонка is_active в таблицу users")
            
        # Проверяем наличие колонки chat_type в таблице users
        if 'chat_type' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN chat_type TEXT DEFAULT "group"')
            logger.info("Добавлена колонка chat_type в таблицу users")
            
        # Проверяем наличие колонки chat_id в таблице challenges
        cursor.execute("PRAGMA table_info(challenges)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем колонку chat_id в challenges, если её нет
        if 'chat_id' not in columns:
            cursor.execute('ALTER TABLE challenges ADD COLUMN chat_id TEXT')
            logger.info("Добавлена колонка chat_id в таблицу challenges")
            
        # Добавляем колонку is_system в challenges, если её нет
        if 'is_system' not in columns:
            cursor.execute('ALTER TABLE challenges ADD COLUMN is_system BOOLEAN DEFAULT 0')
            logger.info("Добавлена колонка is_system в таблицу challenges")

        # Проверяем наличие колонки chat_id в таблице running_log
        cursor.execute("PRAGMA table_info(running_log)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем колонку chat_id в running_log, если её нет
        if 'chat_id' not in columns:
            cursor.execute('ALTER TABLE running_log ADD COLUMN chat_id TEXT')
            logger.info("Добавлена колонка chat_id в таблицу running_log")
            
            # После добавления колонки обновляем существующие записи
            update_existing_runs_chat_id()
        
        conn.commit()
        logger.info("Структура базы данных успешно обновлена")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении структуры базы данных: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_tables():
    """Создание таблиц, если они не существуют"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Создание таблиц (весь SQL-код создания таблиц)
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                          (user_id TEXT PRIMARY KEY, 
                           username TEXT, 
                           yearly_goal REAL, 
                           yearly_progress REAL)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS running_log
                          (log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                           user_id TEXT, 
                           km REAL, 
                           date_added DATE,
                           notes TEXT)''')
                           
        # Проверяем наличие колонки notes
        cursor.execute("PRAGMA table_info(running_log)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Если колонки notes нет, добавляем её
        if 'notes' not in columns:
            try:
                cursor.execute('ALTER TABLE running_log ADD COLUMN notes TEXT')
                print("Колонка 'notes' успешно добавлена в таблицу running_log")
            except Exception as e:
                print(f"Ошибка при добавлении колонки 'notes': {e}")
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS challenges
                          (challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT,
                           goal_km REAL,
                           start_date DATE,
                           end_date DATE,
                           chat_id TEXT,
                           is_system BOOLEAN DEFAULT 0)''')
        
        # Вызываем функцию добавления недостающих колонок
        add_missing_columns()
        
        logger.info("Проверка структуры базы данных завершена")
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise
    finally:
        conn.close()

# Вызываем функцию при импорте модуля
create_tables() 