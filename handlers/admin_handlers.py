from config.config import ADMIN_USER_IDS
from database.db import get_connection
from datetime import datetime
from utils.formatters import round_km

def register_handlers(bot):
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

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT OR REPLACE INTO group_goals (year, total_goal, description)
                   VALUES (?, ?, ?)''', 
                (year, goal, description)
            )
            conn.commit()
            conn.close()

            bot.reply_to(
                message, 
                f"Общая цель группы на {year} год установлена: {goal} км\n"
                f"Описание: {description}"
            )

        except ValueError:
            bot.reply_to(message, "Некорректное значение цели. Используйте число.")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка: {str(e)}")

    @bot.message_handler(commands=['clearalldata'])
    def clear_all_data(message):
        user_id = str(message.from_user.id)
        if user_id not in ADMIN_USER_IDS:
            bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            tables = ['users', 'running_log', 'group_goals', 'teams', 
                     'team_members', 'challenges', 'challenge_participants']
            
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            
            conn.commit()
            conn.close()
            
            bot.reply_to(message, "Все данные успешно удалены из базы данных.")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при очистке данных: {str(e)}")

    @bot.message_handler(commands=['alldata'])
    def all_data(message):
        user_id = str(message.from_user.id)
        if user_id not in ADMIN_USER_IDS:
            bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            users_data = cursor.fetchall()
            conn.close()

            if not users_data:
                bot.reply_to(message, "База данных пуста.")
                return

            response = "Все данные пользователей:\n\n"
            for user in users_data:
                response += (
                    f"ID: {user[0]}\n"
                    f"Имя: {user[1]}\n"
                    f"Цель: {round_km(user[2])} км\n"
                    f"Прогресс: {round_km(user[3])} км\n\n"
                )

            bot.reply_to(message, response)
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при получении данных: {str(e)}") 