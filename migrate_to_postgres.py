import sqlite3
import psycopg2
import os
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

print("Начинаем миграцию...")

# Подключение к SQLite
sqlite_conn = sqlite3.connect('running_bot.db')
sqlite_cur = sqlite_conn.cursor()

print("Подключились к SQLite")

# Проверяем данные в SQLite
sqlite_cur.execute("SELECT COUNT(*) FROM users")
users_count = sqlite_cur.fetchone()[0]
print(f"Количество пользователей в SQLite: {users_count}")

# Получаем DATABASE_URL из Railway
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise Exception("DATABASE_URL не установлен")

print(f"DATABASE_URL получен: {database_url[:30]}...")

# Парсим URL и подключаемся к PostgreSQL
url = urlparse(database_url)
pg_conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
pg_cur = pg_conn.cursor()

# Создаем таблицы в PostgreSQL
tables = [
    """
    CREATE TABLE IF NOT EXISTS public.users (
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
    CREATE TABLE IF NOT EXISTS public.running_log (
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
    CREATE TABLE IF NOT EXISTS public.group_goals (
        year INTEGER PRIMARY KEY,
        total_goal REAL,
        description TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.yearly_archive (
        year INTEGER,
        user_id TEXT,
        username TEXT,
        yearly_goal REAL,
        yearly_progress REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.teams (
        team_id SERIAL PRIMARY KEY,
        team_name TEXT,
        created_by TEXT,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.team_members (
        team_id INTEGER,
        user_id TEXT,
        joined_at TIMESTAMP,
        FOREIGN KEY(team_id) REFERENCES teams(team_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS public.challenges (
        challenge_id SERIAL PRIMARY KEY,
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
    CREATE TABLE IF NOT EXISTS public.challenge_participants (
        challenge_id INTEGER,
        user_id TEXT,
        progress REAL DEFAULT 0,
        joined_at TIMESTAMP,
        FOREIGN KEY(challenge_id) REFERENCES challenges(challenge_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """
]

try:
    # Создаем таблицы
    for table in tables:
        pg_cur.execute(table)

    # Мигрируем данные из каждой таблицы
    tables_to_migrate = [
        ('users', 'user_id, username, yearly_goal, yearly_progress, is_active, goal_km, chat_type'),
        ('running_log', 'user_id, km, date_added, notes, chat_id, chat_type'),
        ('group_goals', 'year, total_goal, description'),
        ('yearly_archive', 'year, user_id, username, yearly_goal, yearly_progress'),
        ('teams', 'team_name, created_by, created_at'),
        ('team_members', 'team_id, user_id, joined_at'),
        ('challenges', 'title, description, start_date, end_date, goal_km, created_by, chat_id, is_system'),
        ('challenge_participants', 'challenge_id, user_id, progress, joined_at')
    ]

    for table, columns in tables_to_migrate:
        print(f"Миграция таблицы {table}...")
        sqlite_cur.execute(f"SELECT {columns} FROM {table}")
        rows = sqlite_cur.fetchall()
        
        if rows:
            placeholders = ','.join(['%s'] * len(rows[0]))
            insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            pg_cur.executemany(insert_query, rows)

    # Фиксируем изменения
    pg_conn.commit()
    print("Миграция успешно завершена!")

except Exception as e:
    print(f"Ошибка при миграции: {e}")
    pg_conn.rollback()

finally:
    # Закрываем соединения
    sqlite_conn.close()
    pg_conn.close() 