import sqlite3
from config.config import DATABASE_NAME

conn = sqlite3.connect(DATABASE_NAME)
cursor = conn.cursor()

try:
    # Проверяем данные в таблице users
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    print('
Users in database:')
    for user in users:
        print(f'User: {user}')

    # Проверяем данные в таблице running_log
    cursor.execute('SELECT * FROM running_log')
    runs = cursor.fetchall()
    print('
Runs in database:')
    for run in runs:
        print(f'Run: {run}')

except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()