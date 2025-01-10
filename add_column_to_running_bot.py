import sqlite3
import os

DB_NAME = 'running_bot.db'

print(f"\nПроверяем файл: {DB_NAME}")
print(f"Файл существует: {os.path.exists(DB_NAME)}")
if os.path.exists(DB_NAME):
    print(f"Размер файла: {os.path.getsize(DB_NAME)} bytes")
    print(f"Последнее изменение: {os.path.getmtime(DB_NAME)}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # Проверяем текущую структуру таблицы
        print("\nТекущая структура таблицы users:")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"- {col[1]}: {col[2]} (default: {col[4]})")

        # Проверяем наличие колонки chat_type
        if 'chat_type' not in [col[1] for col in columns]:
            print("\nДобавляем колонку chat_type...")
            cursor.execute('ALTER TABLE users ADD COLUMN chat_type TEXT DEFAULT "group"')
            conn.commit()
            print("Колонка chat_type успешно добавлена")

            # Проверяем обновленную структуру
            print("\nОбновленная структура таблицы users:")
            cursor.execute("PRAGMA table_info(users)")
            for col in cursor.fetchall():
                print(f"- {col[1]}: {col[2]} (default: {col[4]})")

            # Проверяем данные
            print("\nПроверяем значения в новой колонке:")
            cursor.execute("SELECT user_id, username, chat_type FROM users LIMIT 5")
            for row in cursor.fetchall():
                print(f"User {row[1]} (ID: {row[0]}): chat_type = {row[2]}")
        else:
            print("\nКолонка chat_type уже существует")

    except sqlite3.OperationalError as e:
        print(f"\nОшибка при работе с базой данных: {e}")
    finally:
        conn.close()
else:
    print("Файл базы данных не найден!")