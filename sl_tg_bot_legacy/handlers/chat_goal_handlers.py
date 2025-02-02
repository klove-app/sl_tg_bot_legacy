from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.models.challenge import Challenge
from database.models.running_log import RunningLog
from datetime import datetime, timedelta
from handlers.base_handler import BaseHandler
from telebot.apihelper import ApiTelegramException
import traceback
from database.models.user import User
from database.models.group_goals import GroupGoals
from utils.bot_instance import bot
from utils.message_templates import (
    CHAT_STATS_TEMPLATE,
    CHAT_GOAL_PROGRESS_TEMPLATE,
    CHAT_GOAL_SET_TEMPLATE,
    CHAT_GOAL_ALREADY_SET_TEMPLATE,
    CHAT_GOAL_NOT_SET_TEMPLATE
)

class ChatGoalHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики целей чата"""
        self.logger.info("Registering chat goal handlers")
        
        # Регистрируем обработчики команд
        self.bot.register_message_handler(
            self.handle_chat_goal,
            commands=['chatgoal']
        )
        
        self.bot.register_message_handler(
            self.handle_set_chat_goal,
            commands=['setchatgoal']
        )
        
        # Регистрируем обработчики callback-ов
        self.bot.register_callback_query_handler(
            self.handle_set_chat_goal_callback,
            func=lambda call: call.data.startswith('set_chat_goal_') or 
                            call.data.startswith('adjust_chat_goal_') or 
                            call.data.startswith('confirm_chat_goal_') or
                            call.data == 'back_to_chat_goal_menu'
        )
        
        # Регистрируем обработчик для ручного ввода цели
        self.bot.register_message_handler(
            self.handle_manual_chat_goal,
            func=lambda message: (
                message.reply_to_message is not None and
                message.reply_to_message.text is not None and
                "Введите цель в километрах" in message.reply_to_message.text
            ),
            content_types=['text']
        )
        
        self.logger.info("Chat goal handlers registered successfully")

    def handle_chat_goal(self, message: Message):
        """Показывает текущую цель чата"""
        self.log_message(message, "chatgoal")
        try:
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            # Получаем текущую цель чата
            challenge = Challenge.get_chat_challenge(chat_id, year)
            
            if not challenge:
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton(
                        "🎯 Установить цель чата",
                        callback_data="set_chat_goal_custom"
                    )
                )
                self.bot.reply_to(
                    message,
                    "❌ В этом чате не установлена общая цель на текущий год",
                    reply_markup=markup
                )
                return
            
            # Получаем базовую статистику
            total_km = challenge.get_total_progress()
            participants_count = challenge.get_participants_count()
            progress = (total_km / challenge.goal_km * 100) if challenge.goal_km > 0 else 0
            
            # Формируем прогресс-бар
            progress_bar = self._generate_progress_bar(progress)
            
            # Получаем статистику за прошлый год для сравнения
            last_year = year - 1
            last_year_stats = RunningLog.get_chat_stats(chat_id, last_year)
            
            # Получаем текущую статистику
            current_month_stats = RunningLog.get_chat_stats(chat_id, year, month=datetime.now().month)
            
            # Получаем топ бегунов
            top_runners = RunningLog.get_top_runners(chat_id, year, limit=3)
            
            # Получаем прогресс за прошлый год на эту же дату
            last_year_progress = RunningLog.get_chat_stats_until_date(
                chat_id,
                last_year,
                datetime.now().date()
            )
            
            # Рассчитываем прогноз достижения цели
            days_passed = (datetime.now() - datetime(year, 1, 1)).days
            days_in_year = 366 if year % 4 == 0 else 365
            expected_progress = (days_passed / days_in_year) * challenge.goal_km
            current_pace = total_km / days_passed * days_in_year if days_passed > 0 else 0
            
            # Формируем сообщение
            response = f"📊 Статистика чата на {year} год\n\n"
            
            # Основная информация о цели
            response += (
                f"🎯 Цель: {challenge.goal_km:.2f} км\n"
                f"{progress_bar} {progress:.2f}%\n"
                f"👥 Общий прогресс: {total_km:.2f} км\n"
                f"👤 Участников: {participants_count}\n\n"
            )
            
            # Прогресс и прогнозы
            response += "📈 Прогресс и прогнозы:\n"
            response += f"├ Ожидаемый прогресс: {expected_progress:.2f} км\n"
            response += f"├ Текущий темп: {current_pace:.2f} км/год\n"
            if current_pace > 0:
                days_to_goal = (challenge.goal_km - total_km) / (current_pace / days_in_year)
                goal_date = datetime.now() + timedelta(days=days_to_goal)
                if goal_date.year == year:
                    response += f"└ Цель будет достигнута: {goal_date.strftime('%d.%m.%Y')}\n\n"
                else:
                    response += "└ При текущем темпе цель не будет достигнута в этом году\n\n"
            
            # Статистика за текущий месяц
            response += "📅 За текущий месяц:\n"
            response += f"├ Пройдено: {current_month_stats['total_km']:.2f} км\n"
            response += f"├ Пробежек: {current_month_stats['runs_count']}\n"
            response += f"└ Участников: {current_month_stats['users_count']}\n\n"
            
            # Топ-3 участника
            if top_runners:
                response += "🏆 Топ-3 участника:\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, runner in enumerate(top_runners):
                    user = User.get_by_id(runner['user_id'])
                    username = user.username if user else f"User {runner['user_id']}"
                    response += f"{medals[i]} {username}: {runner['total_km']:.2f} км\n"
                response += "\n"
            
            # Средние показатели
            avg_per_user = total_km / participants_count if participants_count > 0 else 0
            response += "📊 Средние показатели:\n"
            response += f"├ Км на участника: {avg_per_user:.2f} км\n"
            if participants_count > 0 and days_passed > 0:
                avg_daily = total_km / days_passed
                response += f"└ Км в день: {avg_daily:.2f} км\n\n"
            
            # Сравнение с прошлым годом
            if last_year_stats['total_km'] > 0:
                # Получаем прогресс за прошлый год на эту же дату
                last_year_progress = RunningLog.get_chat_stats_until_date(
                    chat_id,
                    last_year,
                    datetime.now().date()
                )
                
                progress_vs_last_year = (total_km / last_year_progress['total_km'] * 100) if last_year_progress['total_km'] > 0 else 0
                
                response += f"📅 Сравнение с {last_year} годом:\n"
                response += f"├ На эту же дату: {last_year_progress['total_km']:.2f} км\n"
                
                # Добавляем информативное сравнение
                km_diff = total_km - last_year_progress['total_km']
                if km_diff > 0:
                    response += f"└ Опережаем на {km_diff:.2f} км (+{progress_vs_last_year - 100:.2f}%) 🚀\n"
                elif km_diff < 0:
                    response += f"└ Отстаем на {abs(km_diff):.2f} км ({progress_vs_last_year:.2f}%) ⚡️\n"
                else:
                    response += "└ Точно такой же результат как в прошлом году 🎯\n"
            
            # Добавляем кнопку изменения цели
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "🎯 Изменить цель",
                    callback_data="set_chat_goal_custom"
                )
            )
            
            self.bot.reply_to(message, response, reply_markup=markup)
            
        except Exception as e:
            self.logger.error(f"Error in handle_chat_goal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении статистики чата")

    def handle_set_chat_goal(self, message: Message):
        """Показывает текущую цель чата"""
        self.log_message(message, "setchatgoal")
        try:
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            # Получаем текущую цель чата
            challenge = Challenge.get_chat_challenge(chat_id, year)
            
            if not challenge:
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton(
                        "🎯 Установить цель чата",
                        callback_data="set_chat_goal_custom"
                    )
                )
                self.bot.reply_to(
                    message,
                    "❌ В этом чате не установлена общая цель на текущий год",
                    reply_markup=markup
                )
                return
            
            # Получаем базовую статистику
            total_km = challenge.get_total_progress()
            participants_count = challenge.get_participants_count()
            progress = (total_km / challenge.goal_km * 100) if challenge.goal_km > 0 else 0
            
            # Формируем прогресс-бар
            progress_bar = self._generate_progress_bar(progress)
            
            # Получаем статистику за прошлый год для сравнения
            last_year = year - 1
            last_year_stats = RunningLog.get_chat_stats(chat_id, last_year)
            
            # Получаем текущую статистику
            current_month_stats = RunningLog.get_chat_stats(chat_id, year, month=datetime.now().month)
            
            # Получаем топ бегунов
            top_runners = RunningLog.get_top_runners(chat_id, year, limit=3)
            
            # Получаем прогресс за прошлый год на эту же дату
            last_year_progress = RunningLog.get_chat_stats_until_date(
                chat_id,
                last_year,
                datetime.now().date()
            )
            
            # Рассчитываем прогноз достижения цели
            days_passed = (datetime.now() - datetime(year, 1, 1)).days
            days_in_year = 366 if year % 4 == 0 else 365
            expected_progress = (days_passed / days_in_year) * challenge.goal_km
            current_pace = total_km / days_passed * days_in_year if days_passed > 0 else 0
            
            # Формируем сообщение
            response = f"📊 Статистика чата на {year} год\n\n"
            
            # Основная информация о цели
            response += (
                f"🎯 Цель: {challenge.goal_km:.2f} км\n"
                f"{progress_bar} {progress:.2f}%\n"
                f"👥 Общий прогресс: {total_km:.2f} км\n"
                f"👤 Участников: {participants_count}\n\n"
            )
            
            # Прогресс и прогнозы
            response += "📈 Прогресс и прогнозы:\n"
            response += f"├ Ожидаемый прогресс: {expected_progress:.2f} км\n"
            response += f"├ Текущий темп: {current_pace:.2f} км/год\n"
            if current_pace > 0:
                days_to_goal = (challenge.goal_km - total_km) / (current_pace / days_in_year)
                goal_date = datetime.now() + timedelta(days=days_to_goal)
                if goal_date.year == year:
                    response += f"└ Цель будет достигнута: {goal_date.strftime('%d.%m.%Y')}\n\n"
                else:
                    response += "└ При текущем темпе цель не будет достигнута в этом году\n\n"
            
            # Статистика за текущий месяц
            response += "📅 За текущий месяц:\n"
            response += f"├ Пройдено: {current_month_stats['total_km']:.2f} км\n"
            response += f"├ Пробежек: {current_month_stats['runs_count']}\n"
            response += f"└ Участников: {current_month_stats['users_count']}\n\n"
            
            # Топ-3 участника
            if top_runners:
                response += "🏆 Топ-3 участника:\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, runner in enumerate(top_runners):
                    user = User.get_by_id(runner['user_id'])
                    username = user.username if user else f"User {runner['user_id']}"
                    response += f"{medals[i]} {username}: {runner['total_km']:.2f} км\n"
                response += "\n"
            
            # Средние показатели
            avg_per_user = total_km / participants_count if participants_count > 0 else 0
            response += "📊 Средние показатели:\n"
            response += f"├ Км на участника: {avg_per_user:.2f} км\n"
            if participants_count > 0 and days_passed > 0:
                avg_daily = total_km / days_passed
                response += f"└ Км в день: {avg_daily:.2f} км\n\n"
            
            # Сравнение с прошлым годом
            if last_year_stats['total_km'] > 0:
                # Получаем прогресс за прошлый год на эту же дату
                last_year_progress = RunningLog.get_chat_stats_until_date(
                    chat_id,
                    last_year,
                    datetime.now().date()
                )
                
                progress_vs_last_year = (total_km / last_year_progress['total_km'] * 100) if last_year_progress['total_km'] > 0 else 0
                
                response += f"📅 Сравнение с {last_year} годом:\n"
                response += f"├ На эту же дату: {last_year_progress['total_km']:.2f} км\n"
                
                # Добавляем информативное сравнение
                km_diff = total_km - last_year_progress['total_km']
                if km_diff > 0:
                    response += f"└ Опережаем на {km_diff:.2f} км (+{progress_vs_last_year - 100:.2f}%) 🚀\n"
                elif km_diff < 0:
                    response += f"└ Отстаем на {abs(km_diff):.2f} км ({progress_vs_last_year:.2f}%) ⚡️\n"
                else:
                    response += "└ Точно такой же результат как в прошлом году 🎯\n"
            
            # Добавляем кнопку изменения цели
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "🎯 Изменить цель",
                    callback_data="set_chat_goal_custom"
                )
            )
            
            self.bot.reply_to(message, response, reply_markup=markup)
            
        except Exception as e:
            self.logger.error(f"Error in handle_set_chat_goal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении статистики чата")

    def handle_set_chat_goal_callback(self, call: CallbackQuery):
        """Обрабатывает callback-запросы для установки цели чата"""
        self.log_message(call.message, f"set_chat_goal_callback: {call.data}")
        try:
            data = call.data.split('_')
            if data[1] == 'custom':
                self.handle_manual_chat_goal(call.message)
            elif data[1] == 'adjust':
                self.handle_adjust_chat_goal(call.message)
            elif data[1] == 'confirm':
                self.handle_confirm_chat_goal(call.message)
            elif data[1] == 'back':
                self.handle_back_to_chat_goal_menu(call.message)
            else:
                self.bot.answer_callback_query(call.id, "❌ Неизвестная команда")
        except Exception as e:
            self.logger.error(f"Error in handle_set_chat_goal_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.answer_callback_query(call.id, "❌ Произошла ошибка при обработке команды")

    def handle_manual_chat_goal(self, message: Message):
        """Обрабатывает ручной ввод цели чата"""
        self.log_message(message, "manual_chat_goal")
        try:
            # Обрабатываем ввод цели
            goal_km = float(message.text.split()[1]) if len(message.text.split()) > 1 else 0
            if goal_km <= 0:
                self.bot.reply_to(message, "❌ Некорректный формат ввода цели")
                return
            
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            # Проверяем, есть ли уже цель для этого года
            challenge = Challenge.get_chat_challenge(chat_id, year)
            if challenge:
                self.bot.reply_to(message, "❌ Цель уже установлена")
                return
            
            # Устанавливаем новую цель
            Challenge.set_chat_challenge(chat_id, year, goal_km)
            
            self.bot.reply_to(message, f"✅ Цель чата на {year} год установлена: {goal_km:.2f} км")
            
        except Exception as e:
            self.logger.error(f"Error in handle_manual_chat_goal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при установке цели чата")

    def handle_adjust_chat_goal(self, message: Message):
        """Обрабатывает изменение цели чата"""
        self.log_message(message, "adjust_chat_goal")
        try:
            # Обрабатываем ввод новой цели
            new_goal_km = float(message.text.split()[1]) if len(message.text.split()) > 1 else 0
            if new_goal_km <= 0:
                self.bot.reply_to(message, "❌ Некорректный формат ввода новой цели")
                return
            
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            # Получаем текущую цель чата
            challenge = Challenge.get_chat_challenge(chat_id, year)
            
            if not challenge:
                self.bot.reply_to(message, "❌ Цель не установлена")
                return
            
            # Устанавливаем новую цель
            Challenge.set_chat_challenge(chat_id, year, new_goal_km)
            
            self.bot.reply_to(message, f"✅ Цель чата на {year} год изменена: {new_goal_km:.2f} км")
            
        except Exception as e:
            self.logger.error(f"Error in handle_adjust_chat_goal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при изменении цели чата")

    def handle_confirm_chat_goal(self, message: Message):
        """Обрабатывает подтверждение установки цели чата"""
        self.log_message(message, "confirm_chat_goal")
        try:
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            # Получаем текущую цель чата
            challenge = Challenge.get_chat_challenge(chat_id, year)
            
            if not challenge:
                self.bot.reply_to(message, "❌ Цель не установлена")
                return
            
            # Получаем базовую статистику
            total_km = challenge.get_total_progress()
            participants_count = challenge.get_participants_count()
            progress = (total_km / challenge.goal_km * 100) if challenge.goal_km > 0 else 0
            
            # Формируем прогресс-бар
            progress_bar = self._generate_progress_bar(progress)
            
            # Получаем статистику за прошлый год для сравнения
            last_year = year - 1
            last_year_stats = RunningLog.get_chat_stats(chat_id, last_year)
            
            # Получаем текущую статистику
            current_month_stats = RunningLog.get_chat_stats(chat_id, year, month=datetime.now().month)
            
            # Получаем топ бегунов
            top_runners = RunningLog.get_top_runners(chat_id, year, limit=3)
            
            # Получаем прогресс за прошлый год на эту же дату
            last_year_progress = RunningLog.get_chat_stats_until_date(
                chat_id,
                last_year,
                datetime.now().date()
            )
            
            # Рассчитываем прогноз достижения цели
            days_passed = (datetime.now() - datetime(year, 1, 1)).days
            days_in_year = 366 if year % 4 == 0 else 365
            expected_progress = (days_passed / days_in_year) * challenge.goal_km
            current_pace = total_km / days_passed * days_in_year if days_passed > 0 else 0
            
            # Формируем сообщение
            response = f"📊 Статистика чата на {year} год\n\n"
            
            # Основная информация о цели
            response += (
                f"🎯 Цель: {challenge.goal_km:.2f} км\n"
                f"{progress_bar} {progress:.2f}%\n"
                f"👥 Общий прогресс: {total_km:.2f} км\n"
                f"👤 Участников: {participants_count}\n\n"
            )
            
            # Прогресс и прогнозы
            response += "📈 Прогресс и прогнозы:\n"
            response += f"├ Ожидаемый прогресс: {expected_progress:.2f} км\n"
            response += f"├ Текущий темп: {current_pace:.2f} км/год\n"
            if current_pace > 0:
                days_to_goal = (challenge.goal_km - total_km) / (current_pace / days_in_year)
                goal_date = datetime.now() + timedelta(days=days_to_goal)
                if goal_date.year == year:
                    response += f"└ Цель будет достигнута: {goal_date.strftime('%d.%m.%Y')}\n\n"
                else:
                    response += "└ При текущем темпе цель не будет достигнута в этом году\n\n"
            
            # Статистика за текущий месяц
            response += "📅 За текущий месяц:\n"
            response += f"├ Пройдено: {current_month_stats['total_km']:.2f} км\n"
            response += f"├ Пробежек: {current_month_stats['runs_count']}\n"
            response += f"└ Участников: {current_month_stats['users_count']}\n\n"
            
            # Топ-3 участника
            if top_runners:
                response += "🏆 Топ-3 участника:\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, runner in enumerate(top_runners):
                    user = User.get_by_id(runner['user_id'])
                    username = user.username if user else f"User {runner['user_id']}"
                    response += f"{medals[i]} {username}: {runner['total_km']:.2f} км\n"
                response += "\n"
            
            # Средние показатели
            avg_per_user = total_km / participants_count if participants_count > 0 else 0
            response += "📊 Средние показатели:\n"
            response += f"├ Км на участника: {avg_per_user:.2f} км\n"
            if participants_count > 0 and days_passed > 0:
                avg_daily = total_km / days_passed
                response += f"└ Км в день: {avg_daily:.2f} км\n\n"
            
            # Сравнение с прошлым годом
            if last_year_stats['total_km'] > 0:
                # Получаем прогресс за прошлый год на эту же дату
                last_year_progress = RunningLog.get_chat_stats_until_date(
                    chat_id,
                    last_year,
                    datetime.now().date()
                )
                
                progress_vs_last_year = (total_km / last_year_progress['total_km'] * 100) if last_year_progress['total_km'] > 0 else 0
                
                response += f"📅 Сравнение с {last_year} годом:\n"
                response += f"├ На эту же дату: {last_year_progress['total_km']:.2f} км\n"
                
                # Добавляем информативное сравнение
                km_diff = total_km - last_year_progress['total_km']
                if km_diff > 0:
                    response += f"└ Опережаем на {km_diff:.2f} км (+{progress_vs_last_year - 100:.2f}%) 🚀\n"
                elif km_diff < 0:
                    response += f"└ Отстаем на {abs(km_diff):.2f} км ({progress_vs_last_year:.2f}%) ⚡️\n"
                else:
                    response += "└ Точно такой же результат как в прошлом году 🎯\n"
            
            # Добавляем кнопку подтверждения
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data="confirm_chat_goal_yes"
                )
            )
            
            self.bot.reply_to(message, response, reply_markup=markup)
            
        except Exception as e:
            self.logger.error(f"Error in handle_confirm_chat_goal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при подтверждении установки цели чата")

    def handle_back_to_chat_goal_menu(self, message: Message):
        """Обрабатывает возврат к меню установки цели чата"""
        self.log_message(message, "back_to_chat_goal_menu")
        try:
            # Получаем текущую цель чата
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            challenge = Challenge.get_chat_challenge(chat_id, year)
            
            if not challenge:
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton(
                        "🎯 Установить цель чата",
                        callback_data="set_chat_goal_custom"
                    )
                )
                self.bot.reply_to(
                    message,
                    "❌ В этом чате не установлена общая цель на текущий год",
                    reply_markup=markup
                )
                return
            
            # Получаем базовую статистику
            total_km = challenge.get_total_progress()
            participants_count = challenge.get_participants_count()
            progress = (total_km / challenge.goal_km * 100) if challenge.goal_km > 0 else 0
            
            # Формируем прогресс-бар
            progress_bar = self._generate_progress_bar(progress)
            
            # Получаем статистику за прошлый год для сравнения
            last_year = year - 1
            last_year_stats = RunningLog.get_chat_stats(chat_id, last_year)
            
            # Получаем текущую статистику
            current_month_stats = RunningLog.get_chat_stats(chat_id, year, month=datetime.now().month)
            
            # Получаем топ бегунов
            top_runners = RunningLog.get_top_runners(chat_id, year, limit=3)
            
            # Получаем прогресс за прошлый год на эту же дату
            last_year_progress = RunningLog.get_chat_stats_until_date(
                chat_id,
                last_year,
                datetime.now().date()
            )
            
            # Рассчитываем прогноз достижения цели
            days_passed = (datetime.now() - datetime(year, 1, 1)).days
            days_in_year = 366 if year % 4 == 0 else 365
            expected_progress = (days_passed / days_in_year) * challenge.goal_km
            current_pace = total_km / days_passed * days_in_year if days_passed > 0 else 0
            
            # Формируем сообщение
            response = f"📊 Статистика чата на {year} год\n\n"
            
            # Основная информация о цели
            response += (
                f"🎯 Цель: {challenge.goal_km:.2f} км\n"
                f"{progress_bar} {progress:.2f}%\n"
                f"👥 Общий прогресс: {total_km:.2f} км\n"
                f"👤 Участников: {participants_count}\n\n"
            )
            
            # Прогресс и прогнозы
            response += "📈 Прогресс и прогнозы:\n"
            response += f"├ Ожидаемый прогресс: {expected_progress:.2f} км\n"
            response += f"├ Текущий темп: {current_pace:.2f} км/год\n"
            if current_pace > 0:
                days_to_goal = (challenge.goal_km - total_km) / (current_pace / days_in_year)
                goal_date = datetime.now() + timedelta(days=days_to_goal)
                if goal_date.year == year:
                    response += f"└ Цель будет достигнута: {goal_date.strftime('%d.%m.%Y')}\n\n"
                else:
                    response += "└ При текущем темпе цель не будет достигнута в этом году\n\n"
            
            # Статистика за текущий месяц
            response += "📅 За текущий месяц:\n"
            response += f"├ Пройдено: {current_month_stats['total_km']:.2f} км\n"
            response += f"├ Пробежек: {current_month_stats['runs_count']}\n"
            response += f"└ Участников: {current_month_stats['users_count']}\n\n"
            
            # Топ-3 участника
            if top_runners:
                response += "🏆 Топ-3 участника:\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, runner in enumerate(top_runners):
                    user = User.get_by_id(runner['user_id'])
                    username = user.username if user else f"User {runner['user_id']}"
                    response += f"{medals[i]} {username}: {runner['total_km']:.2f} км\n"
                response += "\n"
            
            # Средние показатели
            avg_per_user = total_km / participants_count if participants_count > 0 else 0
            response += "📊 Средние показатели:\n"
            response += f"├ Км на участника: {avg_per_user:.2f} км\n"
            if participants_count > 0 and days_passed > 0:
                avg_daily = total_km / days_passed
                response += f"└ Км в день: {avg_daily:.2f} км\n\n"
            
            # Сравнение с прошлым годом
            if last_year_stats['total_km'] > 0:
                # Получаем прогресс за прошлый год на эту же дату
                last_year_progress = RunningLog.get_chat_stats_until_date(
                    chat_id,
                    last_year,
                    datetime.now().date()
                )
                
                progress_vs_last_year = (total_km / last_year_progress['total_km'] * 100) if last_year_progress['total_km'] > 0 else 0
                
                response += f"📅 Сравнение с {last_year} годом:\n"
                response += f"├ На эту же дату: {last_year_progress['total_km']:.2f} км\n"
                
                # Добавляем информативное сравнение
                km_diff = total_km - last_year_progress['total_km']
                if km_diff > 0:
                    response += f"└ Опережаем на {km_diff:.2f} км (+{progress_vs_last_year - 100:.2f}%) 🚀\n"
                elif km_diff < 0:
                    response += f"└ Отстаем на {abs(km_diff):.2f} км ({progress_vs_last_year:.2f}%) ⚡️\n"
                else:
                    response += "└ Точно такой же результат как в прошлом году 🎯\n"
            
            # Добавляем кнопку изменения цели
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "🎯 Изменить цель",
                    callback_data="set_chat_goal_custom"
                )
            )
            
            self.bot.reply_to(message, response, reply_markup=markup)
            
        except Exception as e:
            self.logger.error(f"Error in handle_back_to_chat_goal_menu: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при возврате к меню установки цели чата") 