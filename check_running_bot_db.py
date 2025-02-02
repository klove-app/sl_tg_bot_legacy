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
        # Проверяем структуру таблицы users
        print("\nСтруктура таблицы users:")
        cursor.execute("PRAGMA table_info(users)")
        for col in cursor.fetchall():
            print(f"- {col[1]}: {col[2]} (default: {col[4]})")

        # Проверяем данные в таблице users
        print("\nДанные в таблице users:")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        if users:
            for user in users:
                print(f"User: {user}")
        else:
            print("Таблица users пуста")

        # Проверяем данные в таблице running_log
        print("\nДанные в таблице running_log:")
        cursor.execute("SELECT * FROM running_log ORDER BY date_added DESC LIMIT 5")
        runs = cursor.fetchall()
        if runs:
            for run in runs:
                print(f"Run: {run}")
        else:
            print("Таблица running_log пуста")

        # Проверяем все таблицы в базе
        print("\nВсе таблицы в базе данных:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")

    except sqlite3.OperationalError as e:
        print(f"Ошибка при чтении базы данных: {e}")
    finally:
        conn.close()
else:
    print("Файл базы данных не найден!") 