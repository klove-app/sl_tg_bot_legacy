import sqlite3
import psycopg2
import os
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
import time

# Загружаем переменные окружения из .env файла
load_dotenv()

# Константы
BATCH_SIZE = 50  # Размер пакета для миграции
CONNECT_TIMEOUT = 10  # Таймаут подключения в секундах

print("Начинаем миграцию...")

try:
    # Подключение к SQLite
    sqlite_conn = sqlite3.connect('running_bot.db')
    sqlite_cur = sqlite_conn.cursor()

    print("Подключились к SQLite")

    # Проверяем данные в SQLite для каждой таблицы
    tables_info = [
        'users', 'running_log', 'group_goals', 'yearly_archive',
        'teams', 'team_members', 'challenges', 'challenge_participants'
    ]
    
    for table in tables_info:
        try:
            sqlite_cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = sqlite_cur.fetchone()[0]
            print(f"Количество записей в таблице {table} (SQLite): {count}")
        except sqlite3.OperationalError as e:
            print(f"Таблица {table} не существует в SQLite: {e}")

    # Получаем DATABASE_URL из Railway
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL не установлен")

    print(f"DATABASE_URL получен: {database_url[:30]}...")

    # Парсим URL и подключаемся к PostgreSQL
    url = urlparse(database_url)
    print("Подключаемся к PostgreSQL...")
    
    pg_conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port,
        connect_timeout=CONNECT_TIMEOUT
    )
    pg_cur = pg_conn.cursor()
    print("Подключились к PostgreSQL успешно")

    # Создаем таблицы в PostgreSQL
    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            yearly_goal REAL,
            yearly_progress REAL,
            is_active BOOLEAN DEFAULT TRUE,
            goal_km FLOAT DEFAULT 0,
            chat_type TEXT DEFAULT 'group'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS running_log (
            log_id SERIAL PRIMARY KEY,
            user_id TEXT,
            km REAL,
            date_added DATE,
            notes TEXT,
            chat_id TEXT,
            chat_type TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS group_goals (
            year INTEGER PRIMARY KEY,
            total_goal REAL,
            description TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS yearly_archive (
            year INTEGER,
            user_id TEXT,
            username TEXT,
            yearly_goal REAL,
            yearly_progress REAL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS teams (
            team_id SERIAL PRIMARY KEY,
            team_name TEXT,
            created_by TEXT,
            created_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS team_members (
            team_id INTEGER,
            user_id TEXT,
            joined_at TIMESTAMP,
            FOREIGN KEY(team_id) REFERENCES teams(team_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS challenges (
            challenge_id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            start_date DATE,
            end_date DATE,
            goal_km REAL,
            created_by TEXT,
            chat_id TEXT,
            is_system BOOLEAN DEFAULT FALSE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS challenge_participants (
            challenge_id INTEGER,
            user_id TEXT,
            progress REAL DEFAULT 0,
            joined_at TIMESTAMP,
            FOREIGN KEY(challenge_id) REFERENCES challenges(challenge_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """
    ]

    print("Создаем таблицы в PostgreSQL...")
    for table in tables:
        try:
            pg_cur.execute(table)
            print(f"Таблица создана успешно: {table.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()}")
        except Exception as e:
            print(f"Ошибка при создании таблицы: {e}")
    
    pg_conn.commit()
    print("Все таблицы созданы успешно")

    # Очищаем таблицы перед миграцией
    print("\nОчищаем таблицы в PostgreSQL...")
    for table in reversed(tables_info):  # Реверсируем порядок для правильной очистки с учетом внешних ключей
        try:
            pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"Таблица {table} очищена")
        except Exception as e:
            print(f"Ошибка при очистке таблицы {table}: {e}")
    pg_conn.commit()
    print("Все таблицы очищены")

    # Функция для преобразования значений
    def convert_row(row, table_name):
        row = list(row)
        if table_name == 'users':
            # Преобразуем is_active из 0/1 в False/True
            row[4] = bool(row[4])
        elif table_name == 'challenges':
            # Преобразуем is_system из 0/1 в False/True
            row[8] = bool(row[8])  # Теперь is_system находится в позиции 8, так как мы добавили challenge_id
        return tuple(row)

    # Мигрируем данные из каждой таблицы
    tables_to_migrate = [
        ('users', 'user_id, username, yearly_goal, yearly_progress, is_active, goal_km, chat_type'),
        ('running_log', 'user_id, km, date_added, notes, chat_id, chat_type'),
        ('group_goals', 'year, total_goal, description'),
        ('yearly_archive', 'year, user_id, username, yearly_goal, yearly_progress'),
        ('teams', 'team_name, created_by, created_at'),
        ('team_members', 'team_id, user_id, joined_at'),
        ('challenges', 'challenge_id, title, description, start_date, end_date, goal_km, created_by, chat_id, is_system'),
        ('challenge_participants', 'challenge_id, user_id, progress, joined_at')
    ]

    # Словарь для хранения соответствия ID челленджей
    challenge_id_map = {}

    for table, columns in tables_to_migrate:
        try:
            print(f"\nМиграция таблицы {table}...")
            
            if table == 'challenges':
                # Получаем челленджи с их ID из SQLite
                sqlite_cur.execute(f"SELECT {columns} FROM {table}")
                rows = sqlite_cur.fetchall()
                
                if rows:
                    total_rows = len(rows)
                    print(f"Найдено {total_rows} записей для миграции")
                    
                    # Сохраняем соответствие ID
                    for row in rows:
                        old_id = row[0]  # ID в SQLite
                        converted_row = convert_row(row, table)
                        placeholders = ','.join(['%s'] * len(converted_row))
                        insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING challenge_id"
                        
                        pg_cur.execute(insert_query, converted_row)
                        new_id = pg_cur.fetchone()[0]  # Новый ID в PostgreSQL
                        challenge_id_map[old_id] = new_id
                        pg_conn.commit()
                        
                        print(f"Челлендж {old_id} -> {new_id}")
                    
                    print(f"Миграция таблицы {table} завершена успешно")
                    print(f"Карта соответствия ID челленджей: {challenge_id_map}")
                else:
                    print(f"Таблица {table} пуста, пропускаем")
                
            elif table == 'challenge_participants':
                # Получаем записи участников
                sqlite_cur.execute(f"SELECT {columns} FROM {table}")
                rows = sqlite_cur.fetchall()
                
                if rows:
                    # Преобразуем старые ID в новые
                    converted_rows = []
                    for row in rows:
                        old_challenge_id = row[0]
                        if old_challenge_id in challenge_id_map:
                            new_row = list(row)
                            new_row[0] = challenge_id_map[old_challenge_id]
                            converted_rows.append(tuple(new_row))
                    
                    if converted_rows:
                        total_rows = len(converted_rows)
                        print(f"Найдено {len(rows)} записей, из них {total_rows} с действительными challenge_id")
                        
                        for row in converted_rows:
                            placeholders = ','.join(['%s'] * len(row))
                            insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                            pg_cur.execute(insert_query, row)
                        
                        pg_conn.commit()
                        print(f"Миграция таблицы {table} завершена успешно")
                    else:
                        print("Нет записей с действительными challenge_id")
                else:
                    print(f"Таблица {table} пуста, пропускаем")
            
            else:
                sqlite_cur.execute(f"SELECT {columns} FROM {table}")
                rows = sqlite_cur.fetchall()
                
                if rows:
                    total_rows = len(rows)
                    print(f"Найдено {total_rows} записей для миграции")
                    
                    # Мигрируем данные пакетами
                    for i in range(0, total_rows, BATCH_SIZE):
                        batch = rows[i:i + BATCH_SIZE]
                        converted_batch = [convert_row(row, table) for row in batch]
                        placeholders = ','.join(['%s'] * len(converted_batch[0]))
                        insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                        
                        pg_cur.executemany(insert_query, converted_batch)
                        pg_conn.commit()  # Фиксируем изменения после каждого пакета
                        
                        progress = min((i + BATCH_SIZE), total_rows)
                        print(f"Прогресс: {progress}/{total_rows} записей ({(progress/total_rows*100):.1f}%)")
                    
                    print(f"Миграция таблицы {table} завершена успешно")
                else:
                    print(f"Таблица {table} пуста, пропускаем")

        except Exception as e:
            print(f"Ошибка при миграции таблицы {table}: {e}")
            pg_conn.rollback()  # Откатываем изменения только для текущей таблицы
            continue  # Продолжаем со следующей таблицей

    print("\nМиграция успешно завершена!")

    # Проверяем количество записей в PostgreSQL
    print("\nПроверка количества записей в PostgreSQL:")
    for table in tables_info:
        try:
            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = pg_cur.fetchone()[0]
            print(f"Количество записей в таблице {table} (PostgreSQL): {count}")
        except Exception as e:
            print(f"Ошибка при проверке таблицы {table} в PostgreSQL: {e}")

except Exception as e:
    print(f"\nКритическая ошибка при миграции: {e}")
    if 'pg_conn' in locals():
        pg_conn.rollback()

finally:
    print("\nЗакрываем соединения...")
    # Закрываем соединения
    if 'sqlite_conn' in locals():
        sqlite_conn.close()
        print("SQLite соединение закрыто")
    if 'pg_conn' in locals():
        pg_conn.close()
        print("PostgreSQL соединение закрыто")
    print("Все соединения закрыты")
