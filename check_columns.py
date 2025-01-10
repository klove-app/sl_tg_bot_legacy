import sqlite3
from config.config import DATABASE_NAME

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

try:
    # Получаем структуру таблицы users
    cursor.execute('PRAGMA table_info(users)')
    columns = cursor.fetchall()
    print('Columns in users table:')
    for i, col in enumerate(columns):
        print(f'{i}. {col[1]}: {col[2]} (default: {col[4]})')

except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()