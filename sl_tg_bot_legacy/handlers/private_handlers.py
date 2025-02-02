from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
from handlers.base_handler import BaseHandler
from typing import Optional

class PrivateHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики личных сообщений"""
        self.logger.info("Registering private message handlers")
        
        # Регистрация команд для личных сообщений
        self.bot.register_message_handler(
            self.handle_start,
            commands=['start'],
            func=lambda message: message.chat.type == 'private'
        )
        
        self.bot.register_message_handler(
            self.handle_run,
            commands=['run'],
            func=lambda message: message.chat.type == 'private'
        )
        
        self.bot.register_message_handler(
            self.handle_stats,
            commands=['stats'],
            func=lambda message: message.chat.type == 'private'
        )
        
        self.bot.register_message_handler(
            self.handle_rank,
            commands=['rank'],
            func=lambda message: message.chat.type == 'private'
        )
        
        self.logger.info("Private message handlers registered successfully")

    def handle_start(self, message: Message):
        """Обработчик команды /start в личных сообщениях"""
        user_id = str(message.from_user.id)
        username = message.from_user.username or f"user_{user_id}"
        
        user = User.get_by_id(user_id)
        if not user:
            user = User.create(user_id, username, chat_type='private')
            response = (
                "👋 Привет! Я помогу тебе отслеживать твои пробежки.\n\n"
                "Доступные команды:\n"
                "/run - записать новую пробежку\n"
                "/stats - посмотреть свою статистику\n"
                "/rank - узнать свое место в общем рейтинге"
            )
        else:
            response = (
                "👋 С возвращением!\n\n"
                "Доступные команды:\n"
                "/run - записать новую пробежку\n"
                "/stats - посмотреть свою статистику\n"
                "/rank - узнать свое место в общем рейтинге"
            )
        
        self.bot.reply_to(message, response)

    def handle_run(self, message: Message):
        """Обработчик команды /run в личных сообщениях"""
        self.bot.reply_to(
            message,
            "Введите дистанцию пробежки в километрах (например: 5.2)"
        )
        self.bot.register_next_step_handler(message, self.process_run_distance)

    def process_run_distance(self, message: Message):
        """Обработка введенной дистанции пробежки"""
        try:
            km = float(message.text.strip())
            
            if km > 100:
                self.bot.reply_to(message, "❌ Максимальная дистанция - 100 км")
                return
                
            if RunningLog.add_entry(
                user_id=str(message.from_user.id),
                km=km,
                date_added=datetime.now().date()
            ):
                user = User.get_by_id(str(message.from_user.id))
                total_km = RunningLog.get_user_total_km(str(message.from_user.id))
                
                response = f"✅ Записана пробежка {km:.2f} км!\n"
                if user and user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    response += f"📊 Прогресс: {total_km:.2f} из {user.goal_km:.2f} км ({progress:.2f}%)"
                
                self.bot.reply_to(message, response)
            else:
                self.bot.reply_to(message, "❌ Не удалось сохранить пробежку")
                
        except ValueError:
            self.bot.reply_to(
                message,
                "❌ Пожалуйста, введите корректное число (например: 5.2)"
            )

    def handle_stats(self, message: Message):
        """Обработчик команды /stats в личных сообщениях"""
        user_id = str(message.from_user.id)
        stats = RunningLog.get_personal_stats(user_id)
        
        if stats['runs_count'] == 0:
            response = "У вас пока нет записанных пробежек."
        else:
            response = (
                "📊 Ваша статистика:\n\n"
                f"🏃‍♂️ Всего пробежек: {stats['runs_count']}\n"
                f"📏 Общая дистанция: {stats['total_km']:.2f} км\n"
                f"📈 Средняя дистанция: {stats['average_run']:.2f} км\n"
                f"🎯 Лучшая пробежка: {stats['longest_run']:.2f} км\n"
                f"📅 Активных дней: {stats['active_days']}\n\n"
                "📊 Прогресс по месяцам:\n"
            )
            
            for month_stat in stats['monthly_progress']:
                month_name = {
                    1: 'Январь', 2: 'Февраль', 3: 'Март',
                    4: 'Апрель', 5: 'Май', 6: 'Июнь',
                    7: 'Июль', 8: 'Август', 9: 'Сентябрь',
                    10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
                }[month_stat['month']]
                response += f"{month_name}: {month_stat['km']:.2f} км\n"
        
        self.bot.reply_to(message, response)

    def handle_rank(self, message: Message):
        """Обработчик команды /rank в личных сообщениях"""
        user_id = str(message.from_user.id)
        rank_info = RunningLog.get_user_global_rank(user_id)
        
        if rank_info['rank'] == 0:
            response = "У вас пока нет записанных пробежек для участия в рейтинге."
        else:
            response = (
                "🏆 Ваше место в общем рейтинге:\n\n"
                f"📊 Позиция: {rank_info['rank']} из {rank_info['total_users']}\n"
                f"📏 Общая дистанция: {rank_info['total_km']:.2f} км\n"
            )
            
            # Добавляем топ-5 бегунов
            top_runners = RunningLog.get_top_runners(limit=5)
            if top_runners:
                response += "\n🏃‍♂️ Топ-5 бегунов:\n"
                for i, runner in enumerate(top_runners, 1):
                    user = User.get_by_id(runner['user_id'])
                    username = user.username if user else f"user_{runner['user_id']}"
                    response += f"{i}. {username}: {runner['total_km']:.2f} км\n"
        
        self.bot.reply_to(message, response)

def register_handlers(bot):
    """Регистрирует обработчики личных сообщений"""
    handler = PrivateHandler(bot)
    handler.register() 