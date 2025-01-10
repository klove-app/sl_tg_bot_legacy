import sqlite3

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

try:
    cursor.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name="users"')
    result = cursor.fetchone()
    print('Table schema:')
    print(result[0] if result else 'Table not found')
except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()