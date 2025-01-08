import os
import sys
import re
import traceback
import calendar
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# Добавляем текущую директорию в PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импорты
from bot_instance import bot
from database.base import Base, engine, SessionLocal
from database.logger import logger
from database.models.user import User
from database.models.running_log import RunningLog

# Импортируем обработчики
from handlers.chat_handlers import register_chat_handlers
from handlers.challenge_handlers import register_handlers as register_challenge_handlers
from handlers.team_handlers import register_handlers as register_team_handlers
from handlers.stats_handlers import register_handlers as register_stats_handlers
from handlers.goal_handlers import register_handlers as register_goal_handlers
from handlers.base_handler import BaseHandler
from handlers.chat_goal_handlers import register_handlers as register_chat_goal_handlers
from handlers.reset_handlers import ResetHandler
from handlers.admin_handlers import register_handlers as register_admin_handlers

class MessageHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики текстовых сообщений"""
        self.logger.info("Registering message handlers")
        
        # Регистрируем обработчик текстовых сообщений
        self.bot.register_message_handler(
            self.handle_message,
            content_types=['text'],
            func=lambda message: not message.text.startswith('/')
        )
        
        # Регистрируем обработчик фото
        self.bot.register_message_handler(
            self.handle_photo_run,
            content_types=['photo']
        )
        
        self.logger.info("Message handlers registered successfully")

    def handle_message(self, message):
        """Обрабатывает текстовые сообщения"""
        self.log_message(message, "text")
        
        # Проверяем, что сообщение адресовано боту
        is_bot_mentioned = False
        if message.reply_to_message and message.reply_to_message.from_user.id == self.bot.get_me().id:
            is_bot_mentioned = True
        elif self.bot.get_me().username and f"@{self.bot.get_me().username}" in message.text:
            is_bot_mentioned = True
        elif message.chat.type == 'private':
            is_bot_mentioned = True
            
        # Если сообщение не адресовано боту - игнорируем
        if not is_bot_mentioned:
            return
        
        # Пытаемся найти число в сообщении
        match = re.search(r'(\d+[.,]?\d*)', message.text)
        if match:
            try:
                km_str = match.group(1).replace(',', '.')
                km = float(km_str)
                
                if km <= 0:
                    self.bot.reply_to(
                        message,
                        "⚠️ *Некорректная дистанция*\n\n"
                        "Пожалуйста, укажите положительное число километров",
                        parse_mode='Markdown'
                    )
                    return
                    
                user_id = str(message.from_user.id)
                chat_id = str(message.chat.id)
                
                # Получаем или создаем пользователя
                user = User.get_by_id(user_id)
                if not user:
                    username = message.from_user.username or message.from_user.first_name
                    user = User.create(user_id=user_id, username=username)
                    self.logger.info(f"Created new user: {username} ({user_id})")
                
                # Добавляем запись о пробежке
                success = RunningLog.add_entry(
                    user_id=user_id,
                    km=km,
                    date_added=datetime.now().date(),
                    notes=message.text,
                    chat_id=chat_id
                )
                
                if success:
                    # Формируем ответное сообщение
                    total_km = RunningLog.get_user_total_km(user_id)
                    
                    response = (
                        f"🎉 *Пробежка записана!*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"📍 Дистанция: *{km:.2f} км*\n"
                        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
                        f"📝 Всего: *{total_km:.2f} км*\n"
                    )
                    
                    if user.goal_km > 0:
                        progress = (total_km / user.goal_km * 100)
                        remaining = user.goal_km - total_km
                        response += (
                            f"\n🎯 *Годовая цель*\n"
                            f"• Цель: {user.goal_km:.2f} км\n"
                            f"• Прогресс: {progress:.2f}%\n"
                            f"• Осталось: {remaining:.2f} км"
                        )
                    
                    self.bot.reply_to(message, response, parse_mode='Markdown')
                    self.logger.info(f"Logged run: {km}km for user {user_id}")
                else:
                    error_message = (
                        "⚠️ *Не удалось сохранить пробежку*\n\n"
                        "Пожалуйста, попробуйте еще раз или обратитесь к администратору"
                    )
                    self.bot.reply_to(message, error_message, parse_mode='Markdown')
                    self.logger.error(f"Failed to save run for user {user_id}")
                return
                
            except ValueError:
                self.bot.reply_to(
                    message,
                    "⚠️ *Некорректный формат*\n\n"
                    "Пример: `5.2` или `5,2`",
                    parse_mode='Markdown'
                )
                return
            except Exception as e:
                self.logger.error(f"Error saving run: {e}")
                self.logger.error(f"Full traceback: {traceback.format_exc()}")
                error_message = (
                    "😔 *Произошла ошибка*\n\n"
                    "Пожалуйста, попробуйте позже или обратитесь к администратору"
                )
                self.bot.reply_to(message, error_message, parse_mode='Markdown')
                return
        
        # Если сообщение в личном чате и не содержит число
        if message.chat.type == 'private':
            help_message = (
                "*📝 Как записать пробежку:*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "*1.* Просто отправьте километраж:\n"
                "• Пример: `5.2`\n\n"
                "*2.* Добавьте описание:\n"
                "• Пример: `5.2 Утренняя пробежка`\n\n"
                "*3.* Отправьте фото с подписью:\n"
                "• Добавьте к фото текст с километражем\n\n"
                "🔍 Все команды: /help"
            )
            self.bot.reply_to(message, help_message, parse_mode='Markdown')

    def handle_photo_run(self, message):
        """Обработка фотографий с подписью"""
        self.log_message(message, "photo")
        try:
            # Проверяем, что фото адресовано боту
            is_bot_mentioned = False
            if message.reply_to_message and message.reply_to_message.from_user.id == self.bot.get_me().id:
                is_bot_mentioned = True
            elif self.bot.get_me().username and message.caption and f"@{self.bot.get_me().username}" in message.caption:
                is_bot_mentioned = True
            elif message.chat.type == 'private':
                is_bot_mentioned = True

            # Если фото не адресовано боту - игнорируем
            if not is_bot_mentioned:
                return
                
            if not message.caption:
                help_message = (
                    "*📸 Как добавить пробежку с фото:*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "1. Прикрепите фото\n"
                    "2. Добавьте подпись с дистанцией\n"
                    "Пример: `5.2 км Вечерняя пробежка`"
                )
                self.bot.reply_to(message, help_message, parse_mode='Markdown')
                return
                
            # Ищем число в подписи
            match = re.search(r'(\d+[.,]?\d*)', message.caption)
            if not match:
                help_message = (
                    "⚠️ *Не найдена дистанция в подписи*\n\n"
                    "Добавьте к фото подпись с километражем\n"
                    "Пример: `5.2 км Вечерняя пробежка`"
                )
                self.bot.reply_to(message, help_message, parse_mode='Markdown')
                return
                
            km_str = match.group(1).replace(',', '.')
            km = float(km_str)
            
            if km <= 0:
                self.bot.reply_to(
                    message,
                    "⚠️ *Некорректная дистанция*\n\n"
                    "Пожалуйста, укажите положительное число километров",
                    parse_mode='Markdown'
                )
                return
                
            user_id = str(message.from_user.id)
            chat_id = str(message.chat.id)
            
            # Получаем или создаем пользователя
            user = User.get_by_id(user_id)
            if not user:
                username = message.from_user.username or message.from_user.first_name
                user = User.create(user_id=user_id, username=username)
                self.logger.info(f"Created new user: {username} ({user_id})")
            
            # Добавляем запись о пробежке
            success = RunningLog.add_entry(
                user_id=user_id,
                km=km,
                date_added=datetime.now().date(),
                notes=message.caption,
                chat_id=chat_id
            )
            
            if success:
                total_km = RunningLog.get_user_total_km(user_id)
                
                response = (
                    f"🎉 *Пробежка с фото записана!*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📍 Дистанция: *{km:.2f} км*\n"
                    f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
                    f"📝 Всего: *{total_km:.2f} км*"
                )
                
                if user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    remaining = user.goal_km - total_km
                    response += (
                        f"\n\n🎯 *Годовая цель*\n"
                        f"• Цель: {user.goal_km:.2f} км\n"
                        f"• Прогресс: {progress:.2f}%\n"
                        f"• Осталось: {remaining:.2f} км"
                    )
                
                self.bot.reply_to(message, response, parse_mode='Markdown')
                self.logger.info(f"Logged run with photo: {km}km for user {user_id}")
            else:
                error_message = (
                    "⚠️ *Не удалось сохранить пробежку*\n\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору"
                )
                self.bot.reply_to(message, error_message, parse_mode='Markdown')
                self.logger.error(f"Failed to save run with photo for user {user_id}")
                
        except ValueError:
            self.bot.reply_to(
                message,
                "⚠️ *Некорректный формат числа*\n\n"
                "Используйте точку или запятую\n"
                "Пример: `5.2` или `5,2`",
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Error in handle_photo_run: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            error_message = (
                "😔 *Произошла ошибка*\n\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору"
            )
            self.bot.reply_to(message, error_message, parse_mode='Markdown')

    def handle_profile(self, message: Message, user_id=None):
        """Показывает личный кабинет пользователя"""
        self.log_message(message, "profile")
        try:
            # Если user_id не передан, берем из сообщения
            if user_id is None:
                user_id = str(message.from_user.id)
            
            # Используем переданную сессию или создаем новую
            db = SessionLocal()
            try:
                # Получаем или создаем пользователя
                user = db.query(User).filter(User.user_id == user_id).first()
                if not user:
                    username = message.from_user.username or message.from_user.first_name
                    user = User(user_id=user_id, username=username)
                    db.add(user)
                    db.commit()
                
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                # Получаем статистику
                year_stats = RunningLog.get_user_stats(user_id, current_year, db=db)
                month_stats = RunningLog.get_user_stats(user_id, current_year, current_month, db=db)
                best_stats = RunningLog.get_best_stats(user_id, db=db)
                
                # Формируем профиль с HTML-форматированием
                response = f"<b>👤 Профиль {user.username}</b>\n\n"
                
                # Прогресс к цели
                if user.goal_km > 0:
                    progress = (year_stats['total_km'] / user.goal_km * 100)
                    progress_bar = self._generate_progress_bar(progress)
                    response += f"🎯 Цель на {current_year}: {user.goal_km:.2f} км\n"
                    response += f"{progress_bar} {progress:.2f}%\n"
                    response += f"📊 Пройдено: {year_stats['total_km']:.2f} км\n"
                    response += f"⭐️ Осталось: {user.goal_km - year_stats['total_km']:.2f} км\n\n"
                else:
                    response += "🎯 Цель на год не установлена\n\n"
                
                # Статистика за текущий месяц
                month_name = calendar.month_name[current_month]
                response += f"📅 <b>{month_name}</b>\n"
                response += f"├ Пробежек: {month_stats['runs_count']}\n"
                response += f"├ Дистанция: {month_stats['total_km']:.2f} км\n"
                if month_stats['runs_count'] > 0:
                    response += f"└ Средняя: {month_stats['avg_km']:.2f} км\n\n"
                else:
                    response += f"└ Средняя: 0.0 км\n\n"
                
                # Лучшие результаты
                response += f"🏆 <b>Лучшие результаты</b>\n"
                response += f"├ Пробежка: {best_stats['best_run']:.2f} км\n"
                response += f"└ Всего: {best_stats['total_runs']} пробежек\n"
                
                # Создаем клавиатуру
                markup = InlineKeyboardMarkup()
                
                # Основные действия
                markup.row(
                    InlineKeyboardButton("📝 Новая пробежка", callback_data="new_run"),
                    InlineKeyboardButton("🎯 Изменить цель", callback_data="set_goal_custom")
                )
                
                # Дополнительные действия
                markup.row(
                    InlineKeyboardButton("📊 Статистика", callback_data="show_detailed_stats"),
                    InlineKeyboardButton("✏️ История", callback_data="edit_runs")
                )
                
                # Отправляем сообщение
                if hasattr(message, 'message_id'):
                    # Если это callback query, редактируем существующее сообщение
                    self.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        text=response,
                        reply_markup=markup,
                        parse_mode='HTML'
                    )
                else:
                    # Если это новое сообщение, отправляем новое
                    self.bot.reply_to(message, response, reply_markup=markup, parse_mode='HTML')
                    
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_profile: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении профиля")

    def _generate_progress_bar(self, percentage, length=10):
        """Генерирует прогресс-бар заданной длины"""
        filled = int(percentage / (100 / length))
        empty = length - filled
        return '▓' * filled + '░' * empty

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Начало работы с ботом"""
    try:
        user_id = str(message.from_user.id)
        username = message.from_user.username or message.from_user.first_name
        
        user = User.get_by_id(user_id)
        if not user:
            user = User.create(user_id=user_id, username=username)
            logger.info(f"Created new user: {username} ({user_id})")
        
        welcome_message = (
            f"👋 Добро пожаловать, {username}!\n\n"
            "🎯 *RunTracker* поможет вам достигать спортивных целей:\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*1. Записывайте пробежки*\n"
            "• Отправьте дистанцию: `5.2`\n"
            "• Добавьте описание: `5.2 Утренняя пробежка`\n"
            "• Прикрепите фото с подписью\n\n"
            "*2. Отслеживайте прогресс*\n"
            "• /stats - ваша статистика 📊\n"
            "• /history - история пробежек 📅\n"
            "• /mystats - детальный анализ 📈\n\n"
            "*3. Соревнуйтесь*\n"
            "• /top - таблица лидеров 🏆\n"
            "• /challenges - участвуйте в челленджах 🎯\n"
            "• /createteam - создайте команду 👥\n\n"
            "🔍 Используйте /help для просмотра всех команд\n"
            "⚡️ Совет: Установите годовую цель командой /setgoal"
        )
        
        bot.reply_to(message, welcome_message, parse_mode='Markdown')
        logger.info(f"Sent welcome message to user {user_id}")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        error_message = (
            "😔 Произошла ошибка при запуске\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору"
        )
        bot.reply_to(message, error_message)

@bot.message_handler(commands=['help'])
def help_handler(message):
    """Показывает список всех команд"""
    help_text = (
        "*🤖 Команды RunTracker*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*📊 Статистика и анализ*\n"
        "• /stats - основные показатели\n"
        "• /mystats - детальная статистика\n"
        "• /history - ваши пробежки\n"
        "• /top - рейтинг бегунов\n\n"
        "*🎯 Цели и достижения*\n"
        "• /setgoal `<км>` - годовая цель\n"
        "• /progress - текущий прогресс\n\n"
        "*📝 Запись пробежек*\n"
        "• Отправьте километраж: `5.2`\n"
        "• С описанием: `5.2 Парковая пробежка`\n"
        "• Фото с подписью дистанции\n\n"
        "*🏆 Челленджи*\n"
        "• /challenges - активные челленджи\n"
        "• /mychallenges - ваши челленджи\n"
        "• /joinchallenge `<ID>` - участвовать\n"
        "• /leavechallenge `<ID>` - покинуть\n\n"
        "*👥 Команды*\n"
        "• /createteam `<название>` - создать\n"
        "• /jointeam `<ID>` - присоединиться\n"
        "• /teamstats - статистика команды\n\n"
        "💡 Совет: Закрепите бота для быстрого доступа"
    )
    
    bot.reply_to(message, help_text, parse_mode='Markdown')
    logger.info(f"Sent help message to user {message.from_user.id}")

def register_message_handlers(bot):
    """Регистрирует обработчики сообщений"""
    handler = MessageHandler(bot)
    handler.register()

def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Starting bot...")
        
        # Создаем таблицы в базе данных
        Base.metadata.create_all(engine)
        logger.info("Database tables created")
        
        # Регистрируем обработчики
        register_chat_handlers(bot)
        register_challenge_handlers(bot)
        register_team_handlers(bot)
        register_stats_handlers(bot)
        register_goal_handlers(bot)
        register_chat_goal_handlers(bot)
        register_admin_handlers(bot)
        
        # Регистрируем обработчик сброса данных
        reset_handler = ResetHandler(bot)
        reset_handler.register()
        
        # Регистрируем обработчики сообщений
        register_message_handlers(bot)
        
        logger.info("Bot handlers registered")
        
        # Запускаем бота
        logger.info("Bot is running...")
        bot.infinity_polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
   main()