import sqlite3

conn = sqlite3.connect('bot.db')
cursor = conn.cursor()

try:
    # Проверяем текущую структуру таблицы
    cursor.execute('PRAGMA table_info(users)')
    columns = cursor.fetchall()
    print('Current table structure:')
    for col in columns:
        print(f'Column: {col[1]}, Type: {col[2]}')

    # Проверяем, есть ли уже колонка chat_type
    if 'chat_type' not in [col[1] for col in columns]:
        print('
Adding chat_type column...')
        cursor.execute('ALTER TABLE users ADD COLUMN chat_type VARCHAR DEFAULT "group"')
        conn.commit()
        print('Column added successfully')
    else:
        print('
Column chat_type already exists')

    # Проверяем структуру после изменений
    print('
Updated table structure:')
    cursor.execute('PRAGMA table_info(users)')
    columns = cursor.fetchall()
    for col in columns:
        print(f'Column: {col[1]}, Type: {col[2]}')

except sqlite3.OperationalError as e:
    print(f'Error: {e}')
finally:
    conn.close()