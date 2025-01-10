import sqlite3

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE users ADD COLUMN chat_type VARCHAR DEFAULT "group" NOT NULL')
    conn.commit()
    print('Column chat_type added successfully')
except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()