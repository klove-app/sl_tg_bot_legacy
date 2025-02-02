from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
import traceback
from handlers.base_handler import BaseHandler
import calendar
from database.base import SessionLocal
from telebot.apihelper import ApiTelegramException

class StatsHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики статистики"""
        self.logger.info("Registering stats handlers")
        
        # Регистрируем обработчики команд напрямую
        self.bot.register_message_handler(
            self.handle_stats,
            commands=['stats', 'mystats']
        )
        
        self.bot.register_message_handler(
            self.handle_top,
            commands=['top']
        )
        
        self.bot.register_message_handler(
            self.handle_profile,
            commands=['me', 'profile']
        )
        
        # Регистрируем обработчики callback-ов от кнопок
        self.bot.register_callback_query_handler(
            self.handle_set_goal_callback,
            func=lambda call: call.data.startswith('set_goal_') or 
                            call.data.startswith('adjust_goal_') or 
                            call.data.startswith('confirm_goal_') or
                            call.data == 'set_goal_precise'
        )
        
        self.bot.register_callback_query_handler(
            self.handle_detailed_stats_callback,
            func=lambda call: call.data == 'show_detailed_stats'
        )
        
        self.bot.register_callback_query_handler(
            self.handle_edit_runs_callback,
            func=lambda call: call.data == 'edit_runs'
        )
        
        self.bot.register_callback_query_handler(
            self.handle_back_to_profile_callback,
            func=lambda call: call.data == 'back_to_profile'
        )
        
        self.bot.register_callback_query_handler(
            self.handle_edit_run_callback,
            func=lambda call: call.data.startswith('edit_run_')
        )
        
        self.bot.register_callback_query_handler(
            self.handle_delete_run_callback,
            func=lambda call: call.data.startswith('delete_run_')
        )
        
        self.bot.register_callback_query_handler(
            self.handle_confirm_delete_callback,
            func=lambda call: call.data.startswith('confirm_delete_')
        )
        
        self.bot.register_callback_query_handler(
            self.handle_adjust_run_callback,
            func=lambda call: call.data.startswith('adjust_run_')
        )
        
        self.bot.register_callback_query_handler(
            self.handle_new_run_callback,
            func=lambda call: call.data == 'new_run' or call.data.startswith('quick_run_')
        )
        
        self.logger.info("Stats handlers registered successfully")

    def handle_stats(self, message: Message):
        """Показывает статистику пользователя"""
        self.log_message(message, "stats")
        try:
            user_id = str(message.from_user.id)
            self.logger.info(f"Getting user {user_id} from database")
            user = User.get_by_id(user_id)
            if not user:
                self.logger.info(f"User {user_id} not found")
                self.bot.reply_to(message, "❌ Вы еще не зарегистрированы. Отправьте боту свою первую пробежку!")
                return

            current_year = datetime.now().year
            self.logger.info(f"Getting stats for user {user_id} for year {current_year}")
            stats = RunningLog.get_user_stats(user_id, current_year)
            self.logger.info(f"Got stats: {stats}")
            best_stats = RunningLog.get_best_stats(user_id)
            self.logger.info(f"Got best stats: {best_stats}")

            response = f"📊 Статистика {user.username}\n\n"
            response += f"За {current_year} год:\n"
            response += f"🏃‍♂️ Пробежек: {stats['runs_count']}\n"
            response += f"📏 Всего: {stats['total_km']:.2f} км\n"
            response += f"📈 Средняя дистанция: {stats['avg_km']:.2f} км\n"
            
            if user.goal_km > 0:
                progress = (stats['total_km'] / user.goal_km * 100)
                response += f"\n🎯 Цель на год: {user.goal_km:.2f} км\n"
                response += f"✨ Прогресс: {progress:.2f}%\n"
            
            response += f"\n🏆 Лучшие показатели:\n"
            response += f"💪 Лучшая пробежка: {best_stats['best_run']:.2f} км\n"
            response += f"🌟 Общая дистанция: {best_stats['total_km']:.2f} км"

            self.logger.info(f"Sending response: {response}")
            self.bot.reply_to(message, response)
            self.logger.info(f"Sent stats to user {user_id}")
        except Exception as e:
            self.logger.error(f"Error in handle_stats: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении статистики")

    def handle_top(self, message: Message):
        """Показывает топ бегунов и статистику чата"""
        self.log_message(message, "top")
        try:
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            # Получаем топ бегунов
            top_runners = RunningLog.get_top_runners(limit=10, year=current_year)
            self.logger.info(f"Got top runners: {top_runners}")
            
            if not top_runners:
                self.bot.reply_to(message, "📊 Пока нет данных о пробежках")
                return
            
            response = f"📊 Статистика за {current_year} год\n\n"
            
            # Если сообщение из группового чата, добавляем статистику чата
            if message.chat.type in ['group', 'supergroup']:
                chat_id = str(message.chat.id)
                self.logger.info(f"Getting stats for chat {chat_id}")
                
                year_stats = RunningLog.get_chat_stats(chat_id, year=current_year)
                self.logger.info(f"Got year stats: {year_stats}")
                
                month_stats = RunningLog.get_chat_stats(chat_id, year=current_year, month=current_month)
                self.logger.info(f"Got month stats: {month_stats}")
                
                response += f"Общая статистика чата:\n"
                response += f"👥 Участников: {year_stats['users_count']}\n"
                response += f"🏃‍♂️ Пробежек: {year_stats['runs_count']}\n"
                response += f"📏 Общая дистанция: {year_stats['total_km']:.2f} км\n"
                response += f"💪 Лучшая пробежка: {year_stats['best_run']:.2f} км\n\n"
                
                month_name = calendar.month_name[current_month]
                response += f"За {month_name}:\n"
                response += f"📏 Общая дистанция: {month_stats['total_km']:.2f} км\n"
                response += f"🏃‍♂️ Пробежек: {month_stats['runs_count']}\n\n"
            
            # Добавляем топ бегунов
            response += f"🏆 Топ бегунов:\n\n"
            
            for i, runner in enumerate(top_runners, 1):
                user = User.get_by_id(runner['user_id'])
                username = user.username if user else "Unknown"
                
                response += f"{i}. {username}\n"
                response += f"├ Дистанция: {runner['total_km']:.2f} км\n"
                response += f"├ Пробежек: {runner['runs_count']}\n"
                response += f"├ Средняя: {runner['avg_km']:.2f} км\n"
                response += f"└ Лучшая: {runner['best_run']:.2f} км\n\n"
            
            self.logger.info(f"Sending response: {response}")
            self.bot.reply_to(message, response)
            
        except Exception as e:
            self.logger.error(f"Error in handle_top: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении топа бегунов")

    def handle_profile(self, message: Message, user_id=None, db=None):
        """Показывает личный кабинет пользователя"""
        self.log_message(message, "profile")
        try:
            # Если user_id не передан, берем из сообщения
            if user_id is None:
                user_id = str(message.from_user.id)
            
            self.logger.info(f"Getting profile for user {user_id}")
            
            # Используем переданную сессию или создаем новую
            if db is None:
                self.logger.debug("Creating new database session")
                db = SessionLocal()
            else:
                self.logger.debug("Using existing database session")
            
            try:
                # Получаем или создаем пользователя
                user = db.query(User).filter(User.user_id == user_id).first()
                self.logger.debug(f"Found user in database: {user is not None}")
                
                if not user:
                    username = message.from_user.username or message.from_user.first_name
                    chat_type = message.chat.type if message.chat else 'private'
                    self.logger.info(f"Creating new user: {username}, chat_type: {chat_type}")
                    user = User(user_id=user_id, username=username, chat_type=chat_type)
                    db.add(user)
                    db.commit()
                
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                # Получаем статистику
                self.logger.debug(f"Getting year stats for user {user_id}")
                year_stats = RunningLog.get_user_stats(user_id, current_year, db=db)
                self.logger.debug(f"Year stats: {year_stats}")
                
                self.logger.debug(f"Getting month stats for user {user_id}")
                month_stats = RunningLog.get_user_stats(user_id, current_year, current_month, db=db)
                self.logger.debug(f"Month stats: {month_stats}")
                
                self.logger.debug(f"Getting best stats for user {user_id}")
                best_stats = RunningLog.get_best_stats(user_id, db=db)
                self.logger.debug(f"Best stats: {best_stats}")
                
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
                
                # Статистика по типам чатов
                if year_stats.get('chat_stats'):
                    response += f"📊 <b>Статистика по чатам</b>\n"
                    for chat_type, stats in year_stats['chat_stats'].items():
                        chat_type_display = chat_type.capitalize() if chat_type else "Неизвестно"
                        response += f"<b>{chat_type_display}</b>\n"
                        response += f"├ Пробежек: {stats['runs_count']}\n"
                        response += f"├ Дистанция: {stats['total_km']:.2f} км\n"
                        response += f"└ Средняя: {stats['avg_km']:.2f} км\n\n"
                
                # Лучшие результаты
                response += f"🏆 <b>Лучшие результаты</b>\n"
                response += f"├ Пробежка: {best_stats['best_run']:.2f} км\n"
                response += f"└ Всего: {best_stats['total_runs']} пробежек\n"
                
                self.logger.debug(f"Generated response: {response}")
                
                # Создаем клавиатуру
                markup = InlineKeyboardMarkup()
                
                # Основные действия
                markup.row(
                    InlineKeyboardButton("📝 Подробная статистика", callback_data="show_detailed_stats"),
                    InlineKeyboardButton("✏️ Редактировать пробежки", callback_data="edit_runs")
                )
                
                # Кнопка установки цели
                if user.goal_km == 0:
                    markup.row(InlineKeyboardButton("🎯 Установить цель", callback_data="set_goal_0"))
                else:
                    markup.row(InlineKeyboardButton("🎯 Изменить цель", callback_data="set_goal_0"))
                
                # Отправляем сообщение с клавиатурой
                self.logger.info("Sending profile message")
                self.bot.reply_to(message, response, reply_markup=markup, parse_mode='HTML')
                self.logger.info("Profile message sent successfully")
                
            finally:
                if db is not None:
                    self.logger.debug("Closing database session")
                    db.close()
                    
        except Exception as e:
            self.logger.error(f"Error in handle_profile: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении профиля")

    def _generate_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Генерирует прогресс-бар"""
        filled = int(percentage / (100 / length))
        empty = length - filled
        return '▰' * filled + '▱' * empty

    def handle_detailed_stats(self, message: Message, user_id: str = None):
        """Показывает расширенную статистику пользователя в виде статьи"""
        try:
            if not user_id:
                user_id = str(message.from_user.id)
            
            user = User.get_by_id(user_id)
            if not user:
                return "❌ Пользователь не найден"
            
            current_year = datetime.now().year
            current_month = datetime.now().month
            month_name = calendar.month_name[current_month]
            
            year_stats = RunningLog.get_user_stats(user_id, current_year)
            month_stats = RunningLog.get_user_stats(user_id, current_year, current_month)
            best_stats = RunningLog.get_best_stats(user_id)
            
            # Формируем текст статьи
            article = f"📊 Подробная статистика {user.username}\n\n"
            
            # Годовая статистика
            article += f"<b>Статистика за {current_year} год</b>\n"
            article += f"🏃‍♂️ Количество пробежек: {year_stats['runs_count']}\n"
            article += f"📏 Общая дистанция: {year_stats['total_km']:.2f} км\n"
            article += f"📈 Средняя дистанция: {year_stats['avg_km']:.2f} км\n"
            if year_stats['runs_count'] > 0:
                article += f"🔥 Темп роста: {year_stats['total_km'] / (current_month):.2f} км/месяц\n"
            
            # Цель и прогресс
            if user.goal_km > 0:
                progress = (year_stats['total_km'] / user.goal_km * 100)
                article += f"\n<b>Цель на {current_year} год</b>\n"
                article += f"🎯 Цель: {user.goal_km:.2f} км\n"
                article += f"✨ Текущий прогресс: {progress:.2f}%\n"
                article += f"📊 Осталось: {user.goal_km - year_stats['total_km']:.2f} км\n"
            
            # Статистика по типам чатов
            if year_stats.get('chat_stats'):
                article += f"\n<b>Статистика по типам чатов</b>\n"
                for chat_type, stats in year_stats['chat_stats'].items():
                    article += f"\n{chat_type.capitalize()}\n"
                    article += f"├ Количество пробежек: {stats['runs_count']}\n"
                    article += f"├ Общая дистанция: {stats['total_km']:.2f} км\n"
                    article += f"└ Средняя дистанция: {stats['avg_km']:.2f} км\n"
            
            # Месячная статистика
            article += f"\n<b>Статистика за {month_name}</b>\n"
            article += f"🏃‍♂️ Количество пробежек: {month_stats['runs_count']}\n"
            article += f"📏 Общая дистанция: {month_stats['total_km']:.2f} км\n"
            if month_stats['runs_count'] > 0:
                article += f"📈 Средняя дистанция: {month_stats['avg_km']:.2f} км\n"
            
                # Статистика по типам чатов за месяц
                if month_stats.get('chat_stats'):
                    article += f"\nПо типам чатов:\n"
                    for chat_type, stats in month_stats['chat_stats'].items():
                        article += f"{chat_type.capitalize()}: {stats['runs_count']} пробежек, {stats['total_km']:.2f} км\n"
            
            # Лучшие показатели
            article += f"\n<b>Лучшие показатели за все время</b>\n"
            article += f"💪 Лучшая пробежка: {best_stats['best_run']:.2f} км\n"
            article += f"🌟 Общая дистанция: {best_stats['total_km']:.2f} км\n"
            article += f"📊 Всего пробежек: {best_stats['total_runs']}\n"
            
            return article
            
        except Exception as e:
            self.logger.error(f"Error in handle_detailed_stats: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return "❌ Произошла ошибка при получении расширенной статистики"

    def handle_set_goal_callback(self, call):
        """Обрабатывает нажатия на кнопки установки цели"""
        try:
            user_id = str(call.from_user.id)
            
            # Используем одну сессию для всех операций
            db = SessionLocal()
            try:
                # Получаем или создаем пользователя
                user = db.query(User).filter(User.user_id == user_id).first()
                if not user:
                    username = call.from_user.username or call.from_user.first_name
                    user = User(user_id=user_id, username=username)
                    db.add(user)
                    db.commit()

                if call.data == "set_goal_custom":
                    # Получаем статистику за прошлый год
                    last_year = datetime.now().year - 1
                    last_year_stats = RunningLog.get_user_stats(user_id, last_year, db=db)
                    
                    markup = InlineKeyboardMarkup()
                    
                    # Если есть статистика за прошлый год, предлагаем цели на её основе
                    if last_year_stats['total_km'] > 0:
                        last_year_km = last_year_stats['total_km']
                        markup.row(
                            InlineKeyboardButton(
                                f"🎯 Как в {last_year} году: {last_year_km:.0f} км",
                                callback_data=f"set_goal_{last_year_km}"
                            )
                        )
                        markup.row(
                            InlineKeyboardButton(
                                f"🔥 +10% к {last_year}: {last_year_km * 1.1:.0f} км",
                                callback_data=f"set_goal_{last_year_km * 1.1}"
                            )
                        )
                        markup.row(
                            InlineKeyboardButton(
                                f"💪 +25% к {last_year}: {last_year_km * 1.25:.0f} км",
                                callback_data=f"set_goal_{last_year_km * 1.25}"
                            )
                        )
                    
                    # Стандартные варианты целей
                    markup.row(
                        InlineKeyboardButton("500 км", callback_data="set_goal_500"),
                        InlineKeyboardButton("1000 км", callback_data="set_goal_1000"),
                        InlineKeyboardButton("1500 км", callback_data="set_goal_1500")
                    )
                    
                    # Кнопка для точной настройки
                    markup.row(
                        InlineKeyboardButton(
                            "🎯 Точная настройка",
                            callback_data="set_goal_precise"
                        )
                    )
                    
                    # Кнопка возврата
                    markup.row(
                        InlineKeyboardButton(
                            "◀️ Вернуться к профилю",
                            callback_data="back_to_profile"
                        )
                    )
                    
                    response = "Выберите цель на год:\n\n"
                    if last_year_stats['total_km'] > 0:
                        response += f"📊 В {last_year} году вы пробежали: {last_year_stats['total_km']:.2f} км\n"
                        response += f"🏃‍♂️ Количество пробежек: {last_year_stats['runs_count']}\n"
                        response += f"📈 Средняя дистанция: {last_year_stats['avg_km']:.2f} км\n\n"
                    
                    response += "Выберите один из вариантов или настройте точное значение:"
                    
                    try:
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=response,
                            reply_markup=markup
                        )
                    except ApiTelegramException as e:
                        if "message is not modified" not in str(e):
                            raise
                    return
                
                elif call.data == "set_goal_precise":
                    # Показываем интерактивный выбор с кнопками +/-
                    current_goal = user.goal_km if user.goal_km else 1000
                    markup = InlineKeyboardMarkup()
                    
                    # Кнопки изменения значения
                    markup.row(
                        InlineKeyboardButton("➖ 100", callback_data=f"adjust_goal_{current_goal - 100}"),
                        InlineKeyboardButton("➖ 50", callback_data=f"adjust_goal_{current_goal - 50}"),
                        InlineKeyboardButton("➖ 10", callback_data=f"adjust_goal_{current_goal - 10}")
                    )
                    markup.row(
                        InlineKeyboardButton("➕ 10", callback_data=f"adjust_goal_{current_goal + 10}"),
                        InlineKeyboardButton("➕ 50", callback_data=f"adjust_goal_{current_goal + 50}"),
                        InlineKeyboardButton("➕ 100", callback_data=f"adjust_goal_{current_goal + 100}")
                    )
                    
                    # Кнопки подтверждения и отмены
                    markup.row(
                        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_goal_{current_goal}"),
                        InlineKeyboardButton("◀️ Назад", callback_data="set_goal_custom")
                    )
                    
                    response = f"🎯 Настройка цели на год\n\n"
                    response += f"Текущее значение: {current_goal:.0f} км\n\n"
                    response += "Используйте кнопки для изменения значения:"
                    
                    try:
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=response,
                            reply_markup=markup
                        )
                    except ApiTelegramException as e:
                        if "message is not modified" not in str(e):
                            raise
                    return
                
                elif call.data.startswith("adjust_goal_"):
                    # Обрабатываем изменение значения цели
                    new_goal = float(call.data.split('_')[2])
                    if new_goal <= 0:
                        self.bot.answer_callback_query(
                            call.id,
                            "❌ Цель должна быть больше 0"
                        )
                        return
                    
                    markup = InlineKeyboardMarkup()
                    markup.row(
                        InlineKeyboardButton("➖ 100", callback_data=f"adjust_goal_{new_goal - 100}"),
                        InlineKeyboardButton("➖ 50", callback_data=f"adjust_goal_{new_goal - 50}"),
                        InlineKeyboardButton("➖ 10", callback_data=f"adjust_goal_{new_goal - 10}")
                    )
                    markup.row(
                        InlineKeyboardButton("➕ 10", callback_data=f"adjust_goal_{new_goal + 10}"),
                        InlineKeyboardButton("➕ 50", callback_data=f"adjust_goal_{new_goal + 50}"),
                        InlineKeyboardButton("➕ 100", callback_data=f"adjust_goal_{new_goal + 100}")
                    )
                    markup.row(
                        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_goal_{new_goal}"),
                        InlineKeyboardButton("◀️ Назад", callback_data="set_goal_custom")
                    )
                    
                    response = f"🎯 Настройка цели на год\n\n"
                    response += f"Текущее значение: {new_goal:.0f} км\n\n"
                    response += "Используйте кнопки для изменения значения:"
                    
                    try:
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=response,
                            reply_markup=markup
                        )
                    except ApiTelegramException as e:
                        if "message is not modified" not in str(e):
                            raise
                    return
                
                elif call.data.startswith("confirm_goal_") or call.data.startswith("set_goal_"):
                    # Устанавливаем выбранную цель
                    if call.data.startswith("confirm_goal_"):
                        goal = float(call.data.split('_')[2])
                    else:
                        goal = float(call.data.split('_')[2])
                    
                    # Обновляем цель пользователя
                    user.goal_km = goal
                    db.commit()
                    
                    # Отправляем подтверждение
                    self.bot.answer_callback_query(
                        call.id,
                        "✅ Цель успешно установлена"
                    )
                    
                    # Создаем новое сообщение
                    try:
                        # Сначала удаляем старое сообщение
                        self.bot.delete_message(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id
                        )
                    except:
                        pass
                    
                    # Отправляем новое сообщение с профилем
                    response = f"👤 Профиль {user.username}\n\n"
                    
                    # Получаем статистику
                    current_year = datetime.now().year
                    year_stats = RunningLog.get_user_stats(user_id, current_year, db=db)
                    
                    # Статистика за текущий год
                    response += f"📊 Статистика за {current_year} год:\n"
                    response += f"├ 🏃‍♂️ Пробежек: {year_stats['runs_count']}\n"
                    response += f"├ 📏 Всего: {year_stats['total_km']:.2f} км\n"
                    if year_stats['runs_count'] > 0:
                        response += f"└ 📈 Средняя: {year_stats['avg_km']:.2f} км\n\n"
                    else:
                        response += f"└ 📈 Средняя: 0.0 км\n\n"
                    
                    # Цель и прогресс
                    if goal > 0:
                        progress = (year_stats['total_km'] / goal * 100)
                        response += f"🎯 Цель на {current_year} год: {goal:.2f} км\n"
                        response += f"✨ Прогресс: {progress:.2f}%\n"
                    else:
                        response += "🎯 Цель на год не установлена\n"
                    
                    # Создаем клавиатуру
                    markup = InlineKeyboardMarkup()
                    markup.row(
                        InlineKeyboardButton(
                            "📝 Изменить цель на 2025",
                            callback_data="set_goal_custom"
                        )
                    )
                    markup.row(
                        InlineKeyboardButton(
                            "📊 Расширенная статистика",
                            callback_data="show_detailed_stats"
                        )
                    )
                    markup.row(
                        InlineKeyboardButton(
                            "✏️ Редактировать пробежки",
                            callback_data="edit_runs"
                        )
                    )
                    
                    # Отправляем новое сообщение
                    self.bot.send_message(
                        chat_id=call.message.chat.id,
                        text=response,
                        reply_markup=markup
                    )
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_set_goal_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            try:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Произошла ошибка при установке цели"
                )
            except:
                pass

    def handle_detailed_stats_callback(self, call):
        """Обрабатывает нажатие на кнопку расширенной статистики"""
        try:
            user_id = str(call.from_user.id)
            article = self.handle_detailed_stats(call.message, user_id)
            
            # Создаем кнопку возврата к профилю
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "◀️ Вернуться к профилю",
                    callback_data="back_to_profile"
                )
            )
            
            # Отправляем статью с расширенной статистикой
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=article,
                reply_markup=markup,
                parse_mode='HTML'
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_detailed_stats_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при получении расширенной статистики"
            )
    
    def handle_edit_runs_callback(self, call):
        """Обрабатывает нажатие на кнопку редактирования пробежек"""
        try:
            user_id = str(call.from_user.id)
            
            # Получаем последние пробежки пользователя
            runs = RunningLog.get_user_runs(user_id, limit=5)
            
            if not runs:
                self.bot.answer_callback_query(
                    call.id,
                    "У вас пока нет пробежек для редактирования"
                )
                return
            
            response = "🏃‍♂️ Ваши последние пробежки:\n\n"
            
            markup = InlineKeyboardMarkup()
            
            for run in runs:
                run_date = run.date_added.strftime("%d.%m")
                response += f"📅 {run_date}: {run.km:.2f} км\n"
                markup.row(
                    InlineKeyboardButton(
                        f"✏️ {run_date} ({run.km:.2f} км)",
                        callback_data=f"edit_run_{run.log_id}"
                    ),
                    InlineKeyboardButton(
                        "❌",
                        callback_data=f"delete_run_{run.log_id}"
                    )
                )
            
            markup.row(
                InlineKeyboardButton(
                    "◀️ Вернуться к профилю",
                    callback_data="back_to_profile"
                )
            )
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=response,
                reply_markup=markup
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_edit_runs_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при получении списка пробежек"
            )

    def handle_edit_run_callback(self, call):
        """Обрабатывает нажатие на кнопку редактирования конкретной пробежки"""
        try:
            run_id = int(call.data.split('_')[2])
            user_id = str(call.from_user.id)
            
            # Получаем пробежку из базы
            db = SessionLocal()
            try:
                run = db.query(RunningLog).filter(
                    RunningLog.log_id == run_id,
                    RunningLog.user_id == user_id
                ).first()
                
                if not run:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Пробежка не найдена"
                    )
                    return
                
                # Создаем клавиатуру с кнопками изменения дистанции
                markup = InlineKeyboardMarkup()
                current_km = run.km
                
                # Кнопки для изменения на ±0.5, ±1, ±2 км
                markup.row(
                    InlineKeyboardButton(f"➖ 2км", callback_data=f"adjust_run_{run_id}_{current_km - 2}"),
                    InlineKeyboardButton(f"➖ 1км", callback_data=f"adjust_run_{run_id}_{current_km - 1}"),
                    InlineKeyboardButton(f"➖ 0.5км", callback_data=f"adjust_run_{run_id}_{current_km - 0.5}")
                )
                markup.row(
                    InlineKeyboardButton(f"➕ 0.5км", callback_data=f"adjust_run_{run_id}_{current_km + 0.5}"),
                    InlineKeyboardButton(f"➕ 1км", callback_data=f"adjust_run_{run_id}_{current_km + 1}"),
                    InlineKeyboardButton(f"➕ 2км", callback_data=f"adjust_run_{run_id}_{current_km + 2}")
                )
                
                # Кнопки навигации
                markup.row(
                    InlineKeyboardButton("◀️ Назад", callback_data="edit_runs"),
                    InlineKeyboardButton("❌ Удалить", callback_data=f"delete_run_{run_id}")
                )
                
                response = (
                    f"📝 Редактирование пробежки\n\n"
                    f"📅 Дата: {run.date_added.strftime('%d.%m.%Y')}\n"
                    f"📅 Текущая дистанция: {current_km:.2f} км\n\n"
                    f"Выберите изменение дистанции:"
                )
                
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=response,
                    reply_markup=markup
                )
                
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_edit_run_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при редактировании пробежки"
            )

    def handle_adjust_run_callback(self, call):
        """Обрабатывает нажатие на кнопку изменения дистанции пробежки"""
        try:
            # Формат: adjust_run_ID_DISTANCE
            parts = call.data.split('_')
            run_id = int(parts[2])
            new_distance = float(parts[3])
            user_id = str(call.from_user.id)
            
            if new_distance <= 0:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Дистанция должна быть больше 0"
                )
                return
            
            # Проверяем максимальную дистанцию
            if new_distance > 100:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Максимальная дистанция - 100 км"
                )
                return
            
            # Обновляем дистанцию пробежки
            db = SessionLocal()
            try:
                run = db.query(RunningLog).filter(
                    RunningLog.log_id == run_id,
                    RunningLog.user_id == user_id
                ).first()
                
                if not run:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Пробежка не найдена"
                    )
                    return
                
                old_distance = run.km
                run.km = new_distance
                db.commit()
                
                self.bot.answer_callback_query(
                    call.id,
                    f"✅ Дистанция изменена: {old_distance:.2f} → {new_distance:.2f} км"
                )
                
                # Возвращаемся к списку пробежек
                self.handle_edit_runs_callback(call)
                
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_adjust_run_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при изменении дистанции"
            )

    def handle_delete_run_callback(self, call):
        """Обрабатывает нажатие на кнопку удаления пробежки"""
        try:
            run_id = int(call.data.split('_')[2])
            
            # Создаем клавиатуру для подтверждения удаления
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "✅ Да, удалить",
                    callback_data=f"confirm_delete_{run_id}"
                ),
                InlineKeyboardButton(
                    "❌ Нет, отмена",
                    callback_data="edit_runs"
                )
            )
            
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❗️ Вы уверены, что хотите удалить эту пробежку?",
                reply_markup=markup
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_delete_run_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при удалении пробежки"
            )

    def handle_back_to_profile_callback(self, call):
        """Обрабатывает нажатие на кнопку возврата к профилю"""
        try:
            # Создаем новое сообщение профиля
            db = SessionLocal()
            try:
                user_id = str(call.from_user.id)
                self.handle_profile(call.message, user_id, db)
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_back_to_profile_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при возврате к профилю"
            )

    def handle_confirm_delete_callback(self, call):
        """Обрабатывает подтверждение удаления пробежки"""
        try:
            run_id = int(call.data.split('_')[2])
            user_id = str(call.from_user.id)
            
            # Удаляем пробежку
            db = SessionLocal()
            try:
                run = db.query(RunningLog).filter(
                    RunningLog.log_id == run_id,
                    RunningLog.user_id == user_id
                ).first()
                
                if not run:
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Пробежка не найдена"
                    )
                    return
                
                db.delete(run)
                db.commit()
            finally:
                db.close()
            
            self.bot.answer_callback_query(
                call.id,
                "✅ Пробежка успешно удалена"
            )
            
            # Возвращаемся к списку пробежек
            self.handle_edit_runs_callback(call)
            
        except Exception as e:
            self.logger.error(f"Error in handle_confirm_delete_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при удалении пробежки"
            )

    def handle_new_run_callback(self, call):
        """Обрабатывает нажатие на кнопку новой пробежки"""
        try:
            if call.data == 'new_run':
                markup = InlineKeyboardMarkup()
                
                # Популярные дистанции
                markup.row(
                    InlineKeyboardButton("5 км", callback_data="quick_run_5"),
                    InlineKeyboardButton("7.5 км", callback_data="quick_run_7.5"),
                    InlineKeyboardButton("10 км", callback_data="quick_run_10")
                )
                markup.row(
                    InlineKeyboardButton("15 км", callback_data="quick_run_15"),
                    InlineKeyboardButton("21.1 км", callback_data="quick_run_21.1"),
                    InlineKeyboardButton("42.2 км", callback_data="quick_run_42.2")
                )
                
                # Кнопка возврата
                markup.row(
                    InlineKeyboardButton("◀️ Назад", callback_data="back_to_profile")
                )
                
                response = (
                    "🏃‍♂️ <b>Новая пробежка</b>\n\n"
                    "Выберите дистанцию или отправьте сообщением:\n"
                    "• Просто километраж (например: 5.2)\n"
                    "• Километраж и заметку (5.2 Утренняя)\n"
                    "• Фото с подписью, содержащей километраж"
                )
                
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=response,
                    reply_markup=markup,
                    parse_mode='HTML'
                )
                
            elif call.data.startswith('quick_run_'):
                km = float(call.data.split('_')[2])
                user_id = str(call.from_user.id)
                chat_id = str(call.message.chat.id) if call.message.chat.type != 'private' else None
                chat_type = call.message.chat.type if call.message.chat else 'private'
                
                self.logger.info(f"Adding quick run: {km} km for user {user_id}")
                self.logger.debug(f"Chat info - id: {chat_id}, type: {chat_type}")
                
                # Добавляем пробежку
                if RunningLog.add_entry(
                    user_id=user_id,
                    km=km,
                    date_added=datetime.now().date(),
                    chat_id=chat_id,
                    chat_type=chat_type
                ):
                    self.logger.info("Run entry added successfully")
                    
                    # Получаем статистику пользователя
                    self.logger.debug("Getting user information")
                    user = User.get_by_id(user_id)
                    
                    self.logger.debug("Getting total km")
                    total_km = RunningLog.get_user_total_km(user_id)
                    self.logger.debug(f"Total km: {total_km}")
                    
                    response = f"✅ Записана пробежка {km:.2f} км!\n"
                    if user and user.goal_km > 0:
                        progress = (total_km / user.goal_km * 100)
                        response += f"📊 Прогресс: {total_km:.2f} из {user.goal_km:.2f} км ({progress:.2f}%)"
                    
                    self.logger.debug(f"Generated response: {response}")
                    
                    self.bot.answer_callback_query(
                        call.id,
                        "✅ Пробежка успешно записана"
                    )
                    
                    # Возвращаемся к профилю
                    self.logger.info("Updating profile view")
                    self.handle_profile(call.message)
                else:
                    self.logger.error("Failed to add run entry")
                    self.bot.answer_callback_query(
                        call.id,
                        "❌ Не удалось сохранить пробежку"
                    )
            
        except Exception as e:
            self.logger.error(f"Error in handle_new_run_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при добавлении пробежки"
            )

def register_handlers(bot):
    """Регистрирует обработчики статистики"""
    handler = StatsHandler(bot)
    handler.register() 