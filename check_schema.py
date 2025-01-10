import sqlite3
from config.config import DATABASE_NAME

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

except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()