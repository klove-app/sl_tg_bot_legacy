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
    # Проверяем данные в таблице users
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    print('\nUsers in database:')
    for user in users:
        print(f'User: {user}')

    # Проверяем данные в таблице running_log с группировкой по годам
    cursor.execute('''
        SELECT 
            strftime('%Y', date_added) as year,
            COUNT(*) as runs_count,
            SUM(km) as total_distance,
            AVG(km) as avg_distance,
            MAX(km) as max_distance
        FROM running_log 
        GROUP BY year
        ORDER BY year DESC
    ''')
    stats = cursor.fetchall()
    print('\nRunning statistics by year:')
    for stat in stats:
        print(f'Year {stat[0]}:')
        print(f'- Total runs: {stat[1]}')
        print(f'- Total distance: {stat[2]:.2f} km')
        print(f'- Average distance: {stat[3]:.2f} km')
        print(f'- Max distance: {stat[4]:.2f} km\n')

    # Показываем последние 5 записей
    print('\nLast 5 runs:')
    cursor.execute('''
        SELECT date_added, km, user_id, chat_id
        FROM running_log
        ORDER BY date_added DESC
        LIMIT 5
    ''')
    last_runs = cursor.fetchall()
    for run in last_runs:
        print(f'Run: {run}')

except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()