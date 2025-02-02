import sqlite3
import os
from config.config import DATABASE_NAME

# Проверяем существование директории
db_dir = os.path.dirname(DATABASE_NAME)
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

try:
    # Получаем структуру таблицы running_log
    cursor.execute('PRAGMA table_info(running_log)')
    columns = cursor.fetchall()
    print('\nColumns in running_log table:')
    for i, col in enumerate(columns):
        print(f'{i}. {col[1]}: {col[2]} (default: {col[4]})')

    # Проверяем существующие таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print('\nTables in database:')
    for table in tables:
        print(f'Table: {table[0]}')

    # Показываем размер базы данных
    print(f'\nDatabase file size: {os.path.getsize(DATABASE_NAME)} bytes')
    print(f'Last modified: {os.path.getmtime(DATABASE_NAME)}')

except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()