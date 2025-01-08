import matplotlib
matplotlib.use('Agg')  # Установка бэкенда до импорта pyplot
import matplotlib.pyplot as plt
import matplotlib.style as style
import matplotlib.colors as mcolors
import sqlite3
import io
from datetime import datetime, date
from telebot import TeleBot
from io import BytesIO
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import calendar

# Регистрируем адаптеры для корректной работы с датами в SQLite
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_adapter(date, lambda d: d.isoformat())

# ver 2.0.0

TOKEN = '6329273445:AAEsQKLCr2BjNvjjFZhdWs224AoAN7UXqno'
bot = TeleBot(TOKEN)
print("Running new version of bot...")  # Добавьте эту строку в начало файла
ADMIN_USER_IDS = ['1431390352']

def round_km(value):
    """Округляет километры до 2 знаков после запятой"""
    return round(float(value), 2) if value is not None else 0.0

def create_tables():
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id TEXT PRIMARY KEY, 
                       username TEXT, 
                       yearly_goal REAL, 
                       yearly_progress REAL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS running_log
                      (log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       user_id TEXT, 
                       km REAL, 
                       date_added DATE,
                       notes TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS group_goals
                     (year INTEGER PRIMARY KEY,
                      total_goal REAL,
                      description TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS teams
                     (team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      team_name TEXT,
                      created_by TEXT,
                      created_at DATETIME)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS team_members
                     (team_id INTEGER,
                      user_id TEXT,
                      joined_at DATETIME,
                      FOREIGN KEY(team_id) REFERENCES teams(team_id),
                      FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS challenges
                     (challenge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      title TEXT,
                      description TEXT,
                      start_date DATE,
                      end_date DATE,
                      goal_km REAL,
                      created_by TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS challenge_participants
                     (challenge_id INTEGER,
                      user_id TEXT,
                      progress REAL DEFAULT 0,
                      joined_at DATETIME,
                      FOREIGN KEY(challenge_id) REFERENCES challenges(challenge_id),
                      FOREIGN KEY(user_id) REFERENCES users(user_id))''')

    conn.commit()
    conn.close()

def clear_database():
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()

def get_all_data():
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()
    conn.close()
    return data

def load_data(user_id):
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    if user_data:
        user_id, username, yearly_goal, yearly_progress = user_data
        return {
            'user_id': user_id,
            'username': username,
            'yearly_goal': round_km(yearly_goal),
            'yearly_progress': round_km(yearly_progress)
        }
    return None

def save_data(user_id, data):
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO users (user_id, username, yearly_goal, yearly_progress) VALUES (?, ?, ?, ?)",
                   (user_id, data['username'], round_km(data['yearly_goal']), round_km(data.get('yearly_progress', 0))))
    conn.commit()
    conn.close()

def create_user(user_id, username):
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, username, yearly_goal, yearly_progress) VALUES (?, ?, 0, 0)",
                   (user_id, username))
    conn.commit()
    conn.close()

def get_total_km_by_user(user_id, year=None):
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    
    if year is None:
        year = datetime.now().year
    
    cursor.execute("""
        SELECT SUM(km) 
        FROM running_log 
        WHERE user_id=? 
        AND strftime('%Y', date_added) = ?
    """, (user_id, str(year)))
    
    total_km = cursor.fetchone()[0]
    conn.close()
    return round_km(total_km)

def get_total_km_year_all_users():
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    current_year = datetime.now().year
    cursor.execute("""
        SELECT SUM(km) 
        FROM running_log 
        WHERE strftime('%Y', date_added) = ?
    """, (str(current_year),))
    total_km = cursor.fetchone()[0]
    conn.close()
    return round_km(total_km)

def add_km_for_user(user_id, km, message):
    data = load_data(user_id)
    if data:
        km = round_km(km)
        data['yearly_progress'] = get_total_km_by_user(user_id)
        save_data(user_id, data)
        log_running(user_id, km)

        total_km_year = get_total_km_by_user(user_id)
        total_km_year_all_users = get_total_km_year_all_users()
        
        group_goal, goal_description = get_group_goal()
        completion_percentage = round_km((total_km_year_all_users / group_goal * 100) if group_goal > 0 else 0)

        response = f'Пробежка в {km} км зарегистрирована.\n'
        response += f'*Общий прогресс всех участников:* {total_km_year_all_users} км.\n'
        response += f'Общая годовая цель: {round_km(group_goal)} км ({completion_percentage}% выполнено)'
        
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Вы еще не зарегистрировались в боте.")

def log_running(user_id, km):
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("INSERT INTO running_log (user_id, km, date_added) VALUES (?, ?, ?)",
                   (user_id, round_km(km), today))
    conn.commit()
    conn.close()

def get_group_goal(year=None):
    if year is None:
        year = datetime.now().year
    
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT total_goal, description FROM group_goals WHERE year = ?", (year,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return round_km(result[0]), result[1]
    return 0, ""

def get_last_runs(user_id):
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT km, date_added 
        FROM running_log 
        WHERE user_id=? 
        ORDER BY date_added DESC 
        LIMIT 5""", (user_id,))
    runs = cursor.fetchall()
    conn.close()
    return runs

@bot.message_handler(commands=['start'])
def welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "Неизвестный пользователь"

    if not load_data(user_id):
        create_user(user_id, username)
        msg = bot.reply_to(message, "Привет! Какую годовую цель по километрам вы хотите установить?")
        bot.register_next_step_handler(msg, process_goal_step)
    else:
        bot.reply_to(message, "Вы уже зарегистрированы. Используйте команды для управления вашими настройками и отслеживанием пробега.")

def process_goal_step(message):
    try:
        user_id = str(message.from_user.id)
        yearly_goal = round_km(float(message.text.replace(',', '.')))
        data = load_data(user_id)
        if data is not None:
            data['yearly_goal'] = yearly_goal
            save_data(user_id, data)
            bot.reply_to(message, f"Годовая цель установлена: {yearly_goal} км.")
        else:
            bot.reply_to(message, "Произошла ошибка, попробуйте зарегистрироваться снова.")
    except ValueError:
        msg = bot.reply_to(message, "Пожалуйста, укажите корректное числовое значение для годовой цели.")
        bot.register_next_step_handler(msg, process_goal_step)

@bot.message_handler(commands=['go'])
def welcomemenu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('/stats', '/top')
    markup.row('/challenges', '/mychallenges')
    markup.row('/teamstats', '/history')
    markup.row('/help')
    bot.reply_to(message,
                 "Привет! Я бот для отслеживания пробежек. Используй команду /help, чтобы узнать доступные команды.",
                 reply_markup=markup)

@bot.message_handler(commands=['clearalldata'])
def clear_all_data(message):
    user_id = str(message.from_user.id)
    if user_id in ADMIN_USER_IDS:
        clear_database()
        bot.reply_to(message, "Все данные успешно удалены из базы данных.")
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['alldata'])
def all_data(message):
    user_id = str(message.from_user.id)
    if user_id in ADMIN_USER_IDS:
        data = get_all_data()
        response = "Все данные пользователей:\n"
        for row in data:
            response += f"ID: {row[0]}, Имя: {row[1]}, Цель: {round_km(row[2])}, Прогресс: {round_km(row[3])}\n"
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

@bot.message_handler(commands=['clearkm'])
def clear_km(message):
    user_id = str(message.from_user.id)
    data = load_data(user_id)
    if data:
        data['yearly_progress'] = 0
        save_data(user_id, data)
        bot.reply_to(message, "Километры успешно очищены.")
    else:
        bot.reply_to(message, "Вы еще не зарегистрировались в боте.")

@bot.message_handler(commands=['setgoal'])
def set_yearly_goal(message):
    try:
        user_id = str(message.from_user.id)
        text_parts = message.text.split()
        if len(text_parts) >= 2:
            yearly_goal = round_km(float(text_parts[1].replace(',', '.')))
            data = load_data(user_id)

            if data:
                data['yearly_goal'] = yearly_goal
                save_data(user_id, data)
                bot.reply_to(message, f'Годовая цель установлена: {yearly_goal} км.')
            else:
                bot.reply_to(message, "Вы еще не зарегистрировались в боте.")
        else:
            bot.reply_to(message, "Пожалуйста, укажите количество километров.")
    except ValueError:
        bot.reply_to(message, "Некорректное количество километров.")

@bot.message_handler(commands=['setgroupgoal'])
def set_group_goal(message):
    user_id = str(message.from_user.id)
    if user_id not in ADMIN_USER_IDS:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, "Использование: /setgroupgoal [количество_км] [описание]")
            return

        goal = round_km(float(parts[1].replace(',', '.')))
        description = parts[2] if len(parts) > 2 else ""
        year = datetime.now().year

        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO group_goals (year, total_goal, description)
                         VALUES (?, ?, ?)''', (year, goal, description))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"Общая цель группы на {year} год установлена: {goal} км\nОписание: {description}")

    except ValueError:
        bot.reply_to(message, "Некорректное значение цели. Используйте число.")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(func=lambda message: message.text.startswith('@Running_svoiludi_bot'))
def handle_message(message):
    user_id = str(message.from_user.id)
    km_text = message.text[message.text.find(' ') + 1:]
    km_text = km_text.replace(',', '.')

    try:
        km = round_km(float(km_text))
        add_km_for_user(user_id, km, message)
    except ValueError:
        bot.reply_to(message, 'Пожалуйста, укажите корректное количество километров.')

@bot.message_handler(commands=['stats'])
def get_stats(message):
    user_id = str(message.from_user.id)
    data = load_data(user_id)

    if data:
        yearly_goal = data['yearly_goal']
        yearly_progress = round_km(get_total_km_by_user(user_id))

        today = datetime.now()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        days_passed = (today - year_start).days + 1
        remaining_days = (year_start.replace(year=year_start.year + 1) - today).days

        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM running_log 
            WHERE user_id=? 
            AND strftime('%Y', date_added) = ?
        """, (user_id, str(today.year)))
        activity_count = cursor.fetchone()[0]
        conn.close()

        if activity_count > 0:
            average_daily_distance = yearly_progress / days_passed
            projected_yearly_distance = round_km(yearly_progress + (average_daily_distance * remaining_days))
        else:
            projected_yearly_distance = yearly_progress

        if yearly_goal > 0:
            progress_percentage = round_km((yearly_progress / yearly_goal) * 100)
            projected_completion_percentage = round_km((projected_yearly_distance / yearly_goal * 100))
            progress_numeric = f'выполнено {yearly_progress} км из {yearly_goal} км ({progress_percentage}%)'
        else:
            progress_percentage = 0
            projected_completion_percentage = 0
            progress_numeric = "Годовая цель не установлена или равна нулю."

        if progress_percentage >= 100:
            emoji = "🥳"
            message_text = "Вы молодец, идете с опережением плана!"
        elif progress_percentage >= 90:
            emoji = "😊"
            message_text = "Вы молодец, идете почти по плану!"
        else:
            emoji = "😅"
            message_text = "Вы молодец! Но надо еще поднажать!"

        last_runs = get_last_runs(user_id)
        last_runs_info = "\nПоследние пробежки:\n"
        for run in last_runs:
            last_runs_info += f"Дата: {run[1]}, Км: {round_km(run[0])}\n"

        stats_message = f'Пройденные километры в текущем году: {yearly_progress} км.\n'
        
        if activity_count > 0:
            stats_message += f'Прогнозный пробег по году: {projected_yearly_distance} км\n'
        
        stats_message += f'{progress_numeric}\n'
        stats_message += f'{emoji} {message_text}'
        
        if activity_count > 0:
            stats_message += f' Вероятность выполнения цели: {projected_completion_percentage}%\n'
        
        stats_message += last_runs_info
        
        bot.send_message(message.chat.id, stats_message)
    else:
        bot.reply_to(message, "Вы еще не зарегистрировались в боте.")

@bot.message_handler(commands=['top'])
def send_rating(message):
    chat_id = message.chat.id
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    current_year = datetime.now().year
    
    cursor.execute("""
        SELECT u.user_id, u.username, u.yearly_goal, COALESCE(SUM(r.km), 0) as total_km
        FROM users u
        LEFT JOIN running_log r ON u.user_id = r.user_id AND strftime('%Y', r.date_added) = ?
        WHERE u.yearly_goal > 0
        GROUP BY u.user_id
        ORDER BY total_km DESC
    """, (str(current_year),))
    
    users_data = cursor.fetchall()
    
    group_goal, goal_description = get_group_goal()
    total_progress = round_km(get_total_km_year_all_users())
    
    if users_data:
        rating_message = "Рейтинг бегунов по годовым целям:\n\n"
        
        for idx, (user_id, username, yearly_goal, total_km) in enumerate(users_data, 1):
            total_km = round_km(total_km)
            yearly_goal = round_km(yearly_goal)
            completion = round_km((total_km / yearly_goal * 100) if yearly_goal > 0 else 0)
            rating_message += (
                f"{idx}. {username}: {total_km} км "
                f"({completion}% от цели {yearly_goal} км)\n"
            )
        
        if group_goal > 0:
            group_completion = round_km((total_progress / group_goal * 100))
            rating_message += f"\n🎯 Общая цель группы: {round_km(group_goal)} км"
            if goal_description:
                rating_message += f"\n📝 {goal_description}"
            rating_message += f"\n✨ Общий прогресс: {total_progress} км ({group_completion}%)"
        
        chart = create_leaderboard_chart()
        if chart:
            bot.send_photo(chat_id, chart)
        bot.reply_to(message, rating_message)
    else:
        bot.reply_to(message, "Никто из пользователей еще не установил годовую цель.")

@bot.message_handler(commands=['history'])
def show_history(message):
    user_id = str(message.from_user.id)
    
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            strftime('%Y', date_added) as year,
            COUNT(*) as runs_count,
            SUM(km) as total_km,
            (SELECT yearly_goal FROM users WHERE user_id = ? LIMIT 1) as goal
        FROM running_log 
        WHERE user_id = ?
        GROUP BY strftime('%Y', date_added)
        ORDER BY year DESC
    """, (user_id, user_id))
    
    history = cursor.fetchall()
    conn.close()

    if history:
        response = "📚 Ваша статистика по годам:\n\n"
        for year, runs_count, total_km, goal in history:
            total_km = round_km(total_km)
            goal = round_km(goal) if goal else 0
            completion = round_km((total_km / goal * 100) if goal > 0 else 0)
            
            response += f"📅 {year} год:\n"
            response += f"🏃 Всего пробежек: {runs_count}\n"
            response += f"📊 Пройдено: {total_km} км\n"
            if goal > 0:
                response += f"🎯 Цель: {goal} км\n"
                response += f"✨ Выполнено: {completion}%\n"
            response += "\n"
    else:
        response = "История пробежек пока не найдена."

    bot.reply_to(message, response)

@bot.message_handler(commands=['createchallenge'])
def create_challenge(message):
    try:
        parts = message.text.split(maxsplit=5)
        if len(parts) < 5:
            bot.reply_to(message, 
                "Использование: /createchallenge название км ГГГГ-ММ-ДД ГГГГ-ММ-ДД описание\n"
                "Пример: /createchallenge Марафон 42.2 2024-03-01 2024-03-31 Марафон за месяц")
            return

        title = parts[1]
        goal_km = round_km(float(parts[2]))
        start_date = datetime.strptime(parts[3], '%Y-%m-%d').date()
        end_date = datetime.strptime(parts[4], '%Y-%m-%d').date()
        description = parts[5] if len(parts) > 5 else ""
        
        if start_date > end_date:
            bot.reply_to(message, "Дата начала не может быть позже даты окончания")
            return
            
        user_id = str(message.from_user.id)
        
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO challenges (title, goal_km, start_date, end_date, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, goal_km, start_date, end_date, description, user_id))
        
        challenge_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO challenge_participants (challenge_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (challenge_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        response = f"Челлендж '{title}' успешно создан!\n"
        response += f"ID: {challenge_id}\n"
        response += f"Цель: {goal_km} км\n"
        response += f"Период: {start_date} - {end_date}\n"
        response += f"Описание: {description}"
        
        bot.reply_to(message, response)
        
    except ValueError as e:
        bot.reply_to(message, 
            "Ошибка в формате данных. Проверьте правильность дат и километража.\n"
            "Формат: /createchallenge название км ГГГГ-ММ-ДД ГГГГ-ММ-ДД описание")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['joinchallenge'])
def join_challenge(message):
    try:
        args = message.text.split()
        user_id = str(message.from_user.id)
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        # Если ID не указан, показываем список активных челленджей с кнопками
        if len(args) == 1:
            cursor.execute("""
                SELECT c.challenge_id, c.title, c.goal_km, c.start_date, c.end_date,
                       COUNT(cp.user_id) as participants
                FROM challenges c
                LEFT JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
                WHERE c.challenge_id NOT IN (
                    SELECT challenge_id 
                    FROM challenge_participants 
                    WHERE user_id = ?
                )
                GROUP BY c.challenge_id
                ORDER BY c.start_date
            """, (user_id,))
            
            challenges = cursor.fetchall()
            
            if not challenges:
                bot.reply_to(message, "Нет доступных челленджей для присоединения")
                return

            # Создаем инлайн-клавиатуру с кнопками для каждого челленджа
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for challenge_id, title, goal_km, start_date, end_date, participants in challenges:
                button_text = f"{title} ({round_km(goal_km)} км, {participants} уч.)"
                callback_data = f"join_challenge_{challenge_id}"
                markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

            response = "Выберите челлендж для присоединения:"
            bot.reply_to(message, response, reply_markup=markup)
            
        else:
            # Если ID указан, обрабатываем как обычно
            process_challenge_join(message, args[1], user_id)
            
        conn.close()
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

def process_challenge_join(message, challenge_id, user_id):
    """Обработка присоединения к челленджу"""
    try:
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, start_date, end_date 
            FROM challenges 
            WHERE challenge_id = ?
        """, (challenge_id,))
        
        challenge = cursor.fetchone()
        if not challenge:
            bot.reply_to(message, "Челлендж не найден")
            return
            
        cursor.execute("""
            SELECT * FROM challenge_participants 
            WHERE challenge_id = ? AND user_id = ?
        """, (challenge_id, user_id))
        
        if cursor.fetchone():
            bot.reply_to(message, "Вы уже участвуете в этом челлендже")
            return
            
        cursor.execute("""
            INSERT INTO challenge_participants (challenge_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (challenge_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"Вы успешно присоединились к челленджу '{challenge[0]}'!")
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

# Обработчик нажатий на инлайн-кнопки
@bot.callback_query_handler(func=lambda call: call.data.startswith('join_challenge_'))
def callback_join_challenge(call):
    try:
        challenge_id = call.data.split('_')[2]  # Получаем ID челленджа из callback_data
        user_id = str(call.from_user.id)
        
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, start_date, end_date 
            FROM challenges 
            WHERE challenge_id = ?
        """, (challenge_id,))
        
        challenge = cursor.fetchone()
        if not challenge:
            bot.answer_callback_query(call.id, "Челлендж не найден")
            return
            
        cursor.execute("""
            SELECT * FROM challenge_participants 
            WHERE challenge_id = ? AND user_id = ?
        """, (challenge_id, user_id))
        
        if cursor.fetchone():
            bot.answer_callback_query(call.id, "Вы уже участвуете в этом челлендже")
            return
            
        cursor.execute("""
            INSERT INTO challenge_participants (challenge_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (challenge_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()

        # Отправляем новое сообщение вместо ответа на старое
        bot.send_message(call.message.chat.id, f"Вы успешно присоединились к челленджу '{challenge[0]}'!")
        
        # Удаляем сообщение с кнопками
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        # Показываем уведомление о успешном присоединении
        bot.answer_callback_query(call.id, "Успешно присоединились к челленджу!")
        
    except Exception as e:
        bot.answer_callback_query(call.id, "Произошла ошибка при присоединении к челленджу")
        print(f"Error in callback_join_challenge: {str(e)}")

@bot.message_handler(commands=['challenges'])
def list_challenges(message):
    try:
        user_id = str(message.from_user.id)
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.challenge_id, 
                c.title, 
                c.goal_km, 
                c.start_date, 
                c.end_date,
                COUNT(cp.user_id) as participants,
                MAX(CASE WHEN cp.user_id = ? THEN 1 ELSE 0 END) as is_participant
            FROM challenges c
            LEFT JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
            GROUP BY c.challenge_id
            ORDER BY c.start_date
        """, (user_id,))
        
        challenges = cursor.fetchall()
        
        if not challenges:
            bot.reply_to(message, "Челленджей не найдено")
            return
            
        response = "🏃‍♂️ Список челленджей:\n\n"
        
        for challenge in challenges:
            challenge_id, title, goal_km, start_date, end_date, participants, is_participant = challenge
            response += f"🎯 {title} (ID: {challenge_id})\n"
            response += f"Цель: {round_km(goal_km)} км\n"
            response += f"Период: {start_date} - {end_date}\n"
            response += f"Участников: {participants}\n"
            if is_participant:
                response += "✅ Вы участвуете в этом челлендже\n"
            else:
                response += f"👉 Чтобы присоединиться: /joinchallenge {challenge_id}\n"
            response += "\n"
        
        conn.close()
        bot.reply_to(message, response)
        
    except Exception as e:
        print("Error in list_challenges:", str(e))
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")


@bot.message_handler(commands=['challengestats'])
def challenge_stats(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Использование: /challengestats [ID челленджа]")
            return
            
        challenge_id = int(args[1])
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT title, goal_km, start_date, end_date 
            FROM challenges 
            WHERE challenge_id = ?
        """, (challenge_id,))
        
        challenge = cursor.fetchone()
        if not challenge:
            bot.reply_to(message, "Челлендж не найден")
            return
            
        title, goal_km, start_date, end_date = challenge
        
        cursor.execute("""
            SELECT u.username,
                   COALESCE(SUM(r.km), 0) as total_km,
                   COUNT(DISTINCT r.date_added) as active_days
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.user_id
            LEFT JOIN running_log r ON u.user_id = r.user_id
                AND r.date_added BETWEEN ? AND ?
            WHERE cp.challenge_id = ?
            GROUP BY u.username
            ORDER BY total_km DESC
        """, (start_date, end_date, challenge_id))
        
        stats = cursor.fetchall()
        
        response = f"📊 Статистика челленджа '{title}'\n"
        response += f"Цель: {round_km(goal_km)} км\n\n"
        
        for username, total_km, active_days in stats:
            total_km = round_km(total_km)
            completion = round_km((total_km / goal_km * 100) if goal_km > 0 else 0)
            response += f"👤 {username}:\n"
            response += f"Пройдено: {total_km} км ({completion}%)\n"
            response += f"Активных дней: {active_days}\n\n"
        
        conn.close()
        bot.reply_to(message, response)
        
    except ValueError:
        bot.reply_to(message, "Некорректный ID челленджа")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['mychallenges'])
def my_challenges(message):
    try:
        user_id = str(message.from_user.id)
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        # Получаем активные челленджи пользователя
        cursor.execute("""
            SELECT c.challenge_id, c.title, c.goal_km, c.start_date, c.end_date,
                   COALESCE(SUM(r.km), 0) as total_km
            FROM challenges c
            JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
            LEFT JOIN running_log r ON cp.user_id = r.user_id
                AND r.date_added BETWEEN c.start_date AND c.end_date
            WHERE cp.user_id = ? AND c.end_date >= date('now')
            GROUP BY c.challenge_id
            ORDER BY c.end_date
        """, (user_id,))
        
        active_challenges = cursor.fetchall()
        
        if not active_challenges:
            bot.reply_to(message, "У вас нет активных челленджей")
            return
            
        response = "🏃‍♂️ Ваши активные челленджи:\n\n"
        
        for challenge_id, title, goal_km, start_date, end_date, total_km in active_challenges:
            completion = round_km((total_km / goal_km * 100) if goal_km > 0 else 0)
            response += f"🎯 {title} (ID: {challenge_id})\n"
            response += f"Цель: {round_km(goal_km)} км\n"
            response += f"Период: {start_date} - {end_date}\n"
            response += f"Прогресс: {round_km(total_km)} км ({completion}%)\n\n"
        
        conn.close()
        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['leavechallenge'])
def leave_challenge(message):
    try:
        challenge_id = int(message.text.split()[1])
        user_id = str(message.from_user.id)
        
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        # Проверяем, является ли пользователь создателем челленджа
        cursor.execute("""
            SELECT created_by FROM challenges 
            WHERE challenge_id = ?
        """, (challenge_id,))
        
        challenge = cursor.fetchone()
        if challenge and challenge[0] == user_id:
            bot.reply_to(message, "Создатель не может покинуть свой челлендж")
            return
        
        # Удаляем участника из челленджа
        cursor.execute("""
            DELETE FROM challenge_participants 
            WHERE challenge_id = ? AND user_id = ?
        """, (challenge_id, user_id))
        
        if cursor.rowcount > 0:
            conn.commit()
            bot.reply_to(message, "Вы успешно покинули челлендж")
        else:
            bot.reply_to(message, "Вы не являетесь участником этого челленджа")
        
        conn.close()
        
    except ValueError:
        bot.reply_to(message, "Использование: /leavechallenge [ID челленджа]")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['editchallenge'])
def edit_challenge(message):
    try:
        parts = message.text.split(maxsplit=6)
        if len(parts) < 6:
            bot.reply_to(message, 
                "Использование: /editchallenge [ID] название км ГГГГ-ММ-ДД ГГГГ-ММ-ДД описание\n"
                "Пример: /editchallenge 1 Марафон 42.2 2024-03-01 2024-03-31 Марафон за месяц")
            return

        challenge_id = int(parts[1])
        title = parts[2]
        goal_km = round_km(float(parts[3]))
        start_date = datetime.strptime(parts[4], '%Y-%m-%d').date()
        end_date = datetime.strptime(parts[5], '%Y-%m-%d').date()
        description = parts[6] if len(parts) > 6 else ""
        
        user_id = str(message.from_user.id)
        
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        # Проверяем права на редактирование
        cursor.execute("""
            SELECT created_by FROM challenges 
            WHERE challenge_id = ?
        """, (challenge_id,))
        
        challenge = cursor.fetchone()
        if not challenge:
            bot.reply_to(message, "Челлендж не найден")
            return
            
        if challenge[0] != user_id:
            bot.reply_to(message, "Только создатель может редактировать челлендж")
            return
        
        cursor.execute("""
            UPDATE challenges 
            SET title = ?, goal_km = ?, start_date = ?, end_date = ?, description = ?
            WHERE challenge_id = ?
        """, (title, goal_km, start_date, end_date, description, challenge_id))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"Челлендж успешно обновлен!")
        
    except ValueError:
        bot.reply_to(message, "Ошибка в формате данных. Проверьте правильность ID, дат и километража.")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['pastchallenges'])
def past_challenges(message):
    try:
        user_id = str(message.from_user.id)
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.title, c.goal_km, c.start_date, c.end_date,
                   COALESCE(SUM(r.km), 0) as total_km
            FROM challenges c
            JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
            LEFT JOIN running_log r ON cp.user_id = r.user_id
                AND r.date_added BETWEEN c.start_date AND c.end_date
            WHERE cp.user_id = ? AND c.end_date < date('now')
            GROUP BY c.challenge_id
            ORDER BY c.end_date DESC
        """, (user_id,))
        
        past_challenges = cursor.fetchall()
        
        if not past_challenges:
            bot.reply_to(message, "У вас нет завершенных челленджей")
            return
            
        response = "📚 Ваши завершенные челленджи:\n\n"
        
        for title, goal_km, start_date, end_date, total_km in past_challenges:
            completion = round_km((total_km / goal_km * 100) if goal_km > 0 else 0)
            response += f"🎯 {title}\n"
            response += f"Цель: {round_km(goal_km)} км\n"
            response += f"Период: {start_date} - {end_date}\n"
            response += f"Результат: {round_km(total_km)} км ({completion}%)\n"
            if completion >= 100:
                response += "✅ Челлендж выполнен!\n"
            else:
                response += "❌ Челлендж не выполнен\n"
            response += "\n"
        
        conn.close()
        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['createteam'])
def create_team(message):
    try:
        team_name = ' '.join(message.text.split()[1:])
        if not team_name:
            bot.reply_to(message, "Пожалуйста, укажите название команды: /createteam [название]")
            return

        user_id = str(message.from_user.id)
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO teams (team_name, created_by, created_at)
            VALUES (?, ?, ?)
        """, (team_name, user_id, datetime.now()))
        
        team_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (team_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"Команда '{team_name}' успешно создана! ID команды: {team_id}")
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['jointeam'])
def join_team(message):
    try:
        team_id = int(message.text.split()[1])
        user_id = str(message.from_user.id)
        
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT team_name FROM teams WHERE team_id = ?", (team_id,))
        team = cursor.fetchone()
        
        if not team:
            bot.reply_to(message, "Команда не найдена")
            return
            
        cursor.execute("""
            SELECT * FROM team_members 
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))
        
        if cursor.fetchone():
            bot.reply_to(message, "Вы уже состоите в этой команде")
            return
            
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (team_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"Вы успешно присоединились к команде '{team[0]}'!")
        
    except ValueError:
        bot.reply_to(message, "Использование: /jointeam [ID команды]")
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['teamstats'])
def team_stats(message):
    try:
        user_id = str(message.from_user.id)
        conn = sqlite3.connect('running_bot.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.team_id, t.team_name
            FROM teams t
            JOIN team_members tm ON t.team_id = tm.team_id
            WHERE tm.user_id = ?
        """, (user_id,))
        
        teams = cursor.fetchall()
        
        if not teams:
            bot.reply_to(message, "Вы не состоите ни в одной команде")
            return
            
        response = "📊 Статистика команд:\n\n"
        
        for team_id, team_name in teams:
            response += f"👥 Команда: {team_name}\n"
            
            cursor.execute("""
                SELECT u.username,
                       COALESCE(SUM(r.km), 0) as total_km
                FROM users u
                JOIN team_members tm ON u.user_id = tm.user_id
                LEFT JOIN running_log r ON u.user_id = r.user_id
                WHERE tm.team_id = ?
                AND r.date_added >= date('now', '-30 days')
                GROUP BY u.username
                ORDER BY total_km DESC
            """, (team_id,))
            
            member_stats = cursor.fetchall()
            response += "Статистика за последние 30 дней:\n"
            
            for username, km in member_stats:
                km = round_km(km)
                response += f"🏃‍♂️ {username}: {km} км\n"
            
            cursor.execute("""
                SELECT SUM(r.km)
                FROM running_log r
                JOIN team_members tm ON r.user_id = tm.user_id
                WHERE tm.team_id = ?
                AND r.date_added >= date('now', '-30 days')
            """, (team_id,))
            
            total = cursor.fetchone()[0]
            total = round_km(total) if total else 0
            response += f"Общий километраж команды: {total} км\n\n"
        
        conn.close()
        bot.reply_to(message, response)
        
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

@bot.message_handler(commands=['help'])
def help_message(message):
    user_id = str(message.from_user.id)
    response_message = "Доступные команды:\n\n"
    
    response_message += "📊 Статистика и отслеживание:\n"
    response_message += "/mystats - подробная личная статистика\n"
    response_message += "/stats - базовая статистика по километрам\n"
    response_message += "/top - рейтинг пользователей\n"
    response_message += "/history - история пробежек\n\n"
    
    response_message += "🏃‍♂️ Управление пробежками:\n"
    response_message += "/addrun [дата ГГГГ-ММ-ДД] [км] [комментарий] - добавить пробежку\n"
    response_message += "/edit [ID пробежки] [новое количество км] - редактировать пробежку\n"
    response_message += "/setgoal [количество] - установить годовую цель\n\n"
    
    response_message += "👥 Команды:\n"
    response_message += "/createteam [название] - создать команду\n"
    response_message += "/jointeam [ID команды] - присоединиться к команде\n"
    response_message += "/teamstats - статистика команд\n\n"
    
    response_message += "🎯 Челленджи:\n"
    response_message += "/createchallenge название км ГГГГ-ММ-ДД ГГГГ-ММ-ДД описание - создать челлендж\n"
    response_message += "/joinchallenge [ID] - присоединиться к челленджу\n"
    response_message += "/leavechallenge [ID] - покинуть челлендж\n"
    response_message += "/editchallenge [ID] название км ГГГГ-ММ-ДД ГГГГ-ММ-ДД описание - редактировать челлендж\n"
    response_message += "/challenges - список всех активных челленджей\n"
    response_message += "/mychallenges - ваши активные челленджи\n"
    response_message += "/pastchallenges - ваши завершенные челленджи\n"
    response_message += "/challengestats [ID] - статистика челленджа\n\n"

    if user_id in ADMIN_USER_IDS:
        response_message += "🔒 Команды администратора:\n"
        response_message += "/setgroupgoal [количество] [описание] - установить общую цель группы\n"
        response_message += "/alldata - просмотр данных всех пользователей\n"
        response_message += "/clearalldata - очистить все данные (будьте осторожны!)\n\n"

    response_message += "Для добавления пробежки просто отправьте сообщение боту в формате:\n"
    response_message += "@Running_svoiludi_bot [количество_км]"
    
    bot.reply_to(message, response_message)

def create_leaderboard_chart():
    conn = sqlite3.connect('running_bot.db')
    cursor = conn.cursor()
    current_year = datetime.now().year

    cursor.execute("""
        SELECT u.username, COALESCE(SUM(r.km), 0) as total_km
        FROM users u
        LEFT JOIN running_log r ON u.user_id = r.user_id
        AND strftime('%Y', r.date_added) = ?
        GROUP BY u.username
        ORDER BY total_km DESC
        LIMIT 10
    """, (str(current_year),))
    
    data = cursor.fetchall()
    conn.close()

    if not data:
        return None

    usernames = [row[0] for row in data]
    progress = [round_km(row[1]) for row in data]

    plt.figure(figsize=(10, 6))
    plt.style.use('ggplot')
    
    bars = plt.barh(usernames, progress)
    
    for bar in bars:
        width = bar.get_width()
        plt.text(width, bar.get_y() + bar.get_height()/2, 
                f'{round_km(width)}', 
                ha='left', va='center', fontsize=10)

    plt.xlabel('Пройденная дистанция (км)')
    plt.title('Топ бегунов')
    plt.gca().invert_yaxis()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    plt.close()
    buf.seek(0)
    return buf

if __name__ == "__main__":
    print("Инициализация бота...")
    try:
        create_tables()
        print("Таблицы базы данных успешно созданы/проверены")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при инициализации: {e}")   