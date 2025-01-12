from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.models.challenge import Challenge
from database.models.running_log import RunningLog
from datetime import datetime, timedelta
from handlers.base_handler import BaseHandler
from telebot.apihelper import ApiTelegramException
import traceback
from database.db import get_connection

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
            last_year_stats = RunningLog.get_chat_stats_sqlite(chat_id, last_year)
            
            # Получаем статистику за последний месяц
            current_month_stats = RunningLog.get_chat_stats_sqlite(chat_id, year, month=datetime.now().month)
            
            # Получаем топ-3 участников
            top_runners = RunningLog.get_top_runners_sqlite(chat_id, year, limit=3)
            
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
                    response += f"{medals[i]} {runner['user_name']}: {runner['total_km']:.2f} км\n"
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
                # Получаем статистику за прошлый год на текущую дату
                current_date = datetime.now()
                last_year_progress = RunningLog.get_chat_stats_until_date_sqlite(
                    chat_id, 
                    last_year, 
                    current_date.month, 
                    current_date.day
                )
                
                progress_vs_last_year = (total_km / last_year_progress['total_km'] * 100) if last_year_progress['total_km'] > 0 else 0
                
                response += f"📅 Сравнение с {last_year} годом:\n"
                response += f"├ На эту же дату: {last_year_progress['total_km']:.2f} км\n"
                
                # Добавляем информативное сравнение
                km_diff = total_km - last_year_progress['total_km']
                if km_diff > 0:
                    response += f"└ Опережаем на {km_diff:.2f} км (+{progress_vs_last_year - 100:.2f}%) ��\n"
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
        """Начинает процесс установки цели чата"""
        self.log_message(message, "setchatgoal")
        try:
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            # Получаем статистику за прошлый год
            last_year = year - 1
            last_year_stats = RunningLog.get_chat_stats_sqlite(chat_id, last_year)
            
            markup = InlineKeyboardMarkup()
            
            # Если есть статистика за прошлый год, предлагаем цели на её основе
            if last_year_stats['total_km'] > 0:
                last_year_km = last_year_stats['total_km']
                markup.row(
                    InlineKeyboardButton(
                        f"🎯 Как в {last_year} году: {last_year_km:.0f} км",
                        callback_data=f"set_chat_goal_{last_year_km}"
                    )
                )
                markup.row(
                    InlineKeyboardButton(
                        f"🔥 +10% к {last_year}: {last_year_km * 1.1:.0f} км",
                        callback_data=f"set_chat_goal_{last_year_km * 1.1}"
                    )
                )
                markup.row(
                    InlineKeyboardButton(
                        f"💪 +25% к {last_year}: {last_year_km * 1.25:.0f} км",
                        callback_data=f"set_chat_goal_{last_year_km * 1.25}"
                    )
                )
            
            # Стандартные варианты целей
            markup.row(
                InlineKeyboardButton("1000 км", callback_data="set_chat_goal_1000"),
                InlineKeyboardButton("2000 км", callback_data="set_chat_goal_2000"),
                InlineKeyboardButton("3000 км", callback_data="set_chat_goal_3000")
            )
            
            # Кнопка для точной настройки
            markup.row(
                InlineKeyboardButton(
                    "🎯 Точная настройка",
                    callback_data="set_chat_goal_precise"
                )
            )
            
            response = f"Выберите цель для чата на {year} год:\n\n"
            if last_year_stats['total_km'] > 0:
                response += (
                    f"📊 В {last_year} году чат пробежал:\n"
                    f"├ Всего: {last_year_stats['total_km']:.2f} км\n"
                    f"├ Пробежек: {last_year_stats['runs_count']}\n"
                    f"└ Участников: {last_year_stats['users_count']}\n\n"
                )
            
            response += "Выберите один из вариантов или настройте точное значение:"
            
            self.bot.reply_to(message, response, reply_markup=markup)
            
        except Exception as e:
            self.logger.error(f"Error in handle_set_chat_goal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при установке цели")

    def handle_manual_chat_goal(self, message: Message):
        """Обрабатывает ручной ввод цели чата"""
        try:
            self.logger.info(f"Получено сообщение для ручного ввода цели: {message.text}")
            
            # Пытаемся преобразовать введенное значение в число
            goal = float(message.text.replace(',', '.'))
            
            self.logger.info(f"Преобразованное значение цели: {goal}")
            
            if goal <= 0:
                self.bot.reply_to(
                    message,
                    "❌ Цель должна быть больше 0 км"
                )
                return
                
            if goal > 100000:  # Максимальное значение
                self.bot.reply_to(
                    message,
                    "❌ Цель не может быть больше 100000 км"
                )
                return
            
            # Получаем chat_id и год
            chat_id = str(message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            self.logger.info(f"Создаем цель для чата {chat_id} на {year} год: {goal} км")
            
            # Создаем или обновляем челлендж чата
            challenge = Challenge.get_chat_challenge(chat_id, year)
            if challenge:
                challenge.goal_km = goal
                challenge.save()
                self.logger.info("Обновлен существующий челлендж")
            else:
                challenge = Challenge(
                    title=f"Общая цель чата на {year} год",
                    goal_km=goal,
                    start_date=f"{year}-01-01",
                    end_date=f"{year}-12-31",
                    chat_id=chat_id,
                    is_system=False
                )
                challenge.save()
                self.logger.info("Создан новый челлендж")
            
            # Получаем актуальную статистику
            total_km = challenge.get_total_progress()
            participants_count = challenge.get_participants_count()
            progress = (total_km / goal * 100) if goal > 0 else 0
            progress_bar = self._generate_progress_bar(progress)
            
            # Формируем ответное сообщение
            response = (
                f"✅ Установлена общая цель чата на {year} год!\n\n"
                f"🎯 Цель: {goal:.2f} км\n"
                f"{progress_bar} {progress:.2f}%\n"
                f"👥 Текущий прогресс: {total_km:.2f} км\n"
                f"👤 Участников: {participants_count}\n\n"
                f"Все участники чата автоматически участвуют в достижении цели."
            )
            
            # Добавляем кнопку изменения цели
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(
                    "🎯 Изменить цель",
                    callback_data="set_chat_goal_custom"
                )
            )
            
            # Отправляем подтверждение
            self.bot.reply_to(message, response, reply_markup=markup)
            self.logger.info("Отправлено подтверждение установки цели")
            
        except ValueError:
            self.logger.error(f"Ошибка преобразования значения: {message.text}")
            self.bot.reply_to(
                message,
                "❌ Пожалуйста, введите число\n\nПример: 2000 или 2000.5"
            )
        except Exception as e:
            self.logger.error(f"Ошибка в handle_manual_chat_goal: {e}")
            self.logger.error(f"Полный traceback: {traceback.format_exc()}")
            self.bot.reply_to(
                message,
                "❌ Произошла ошибка при установке цели"
            )

    def handle_set_chat_goal_callback(self, call):
        """Обрабатывает нажатия на кнопки установки цели чата"""
        try:
            chat_id = str(call.message.chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            year = datetime.now().year
            
            if call.data == "back_to_chat_goal_menu":
                # Возвращаемся к начальному меню выбора цели
                self.handle_set_chat_goal(call.message)
                return
            
            if call.data == "set_chat_goal_manual":
                # Запрашиваем ручной ввод цели
                msg = self.bot.reply_to(
                    call.message,
                    "📝 Введите цель в километрах:\n\n"
                    "Например: 2000 или 2000.5",
                    reply_markup=InlineKeyboardMarkup().row(
                        InlineKeyboardButton("◀️ Назад", callback_data="back_to_chat_goal_menu")
                    )
                )
                return
            
            if call.data == "set_chat_goal_custom" or call.data == "set_chat_goal_precise":
                # Показываем интерактивный выбор с кнопками +/-
                current_goal = 1000  # Значение по умолчанию
                
                # Если есть существующая цель, берем её
                challenge = Challenge.get_chat_challenge(chat_id, year)
                if challenge:
                    current_goal = challenge.goal_km
                
                markup = InlineKeyboardMarkup()
                
                # Кнопки изменения значения
                markup.row(
                    InlineKeyboardButton("➖ 500", callback_data=f"adjust_chat_goal_{current_goal - 500}"),
                    InlineKeyboardButton("➖ 100", callback_data=f"adjust_chat_goal_{current_goal - 100}"),
                    InlineKeyboardButton("➖ 50", callback_data=f"adjust_chat_goal_{current_goal - 50}")
                )
                markup.row(
                    InlineKeyboardButton("➕ 50", callback_data=f"adjust_chat_goal_{current_goal + 50}"),
                    InlineKeyboardButton("➕ 100", callback_data=f"adjust_chat_goal_{current_goal + 100}"),
                    InlineKeyboardButton("➕ 500", callback_data=f"adjust_chat_goal_{current_goal + 500}")
                )
                
                # Кнопки подтверждения, ручного ввода и возврата
                markup.row(
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_chat_goal_{current_goal}"),
                    InlineKeyboardButton("📝 Ввести вручную", callback_data="set_chat_goal_manual")
                )
                markup.row(
                    InlineKeyboardButton("◀️ Назад", callback_data="back_to_chat_goal_menu")
                )
                
                response = f"🎯 Настройка цели чата на {year} год\n\n"
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
            
            elif call.data.startswith("adjust_chat_goal_"):
                # Обрабатываем изменение значения цели
                new_goal = float(call.data.split('_')[3])
                if new_goal <= 0:
                    if hasattr(call, 'id') and call.id:
                        self.bot.answer_callback_query(
                            call.id,
                            "❌ Цель должна быть больше 0"
                        )
                    return
                
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("➖ 500", callback_data=f"adjust_chat_goal_{new_goal - 500}"),
                    InlineKeyboardButton("➖ 100", callback_data=f"adjust_chat_goal_{new_goal - 100}"),
                    InlineKeyboardButton("➖ 50", callback_data=f"adjust_chat_goal_{new_goal - 50}")
                )
                markup.row(
                    InlineKeyboardButton("➕ 50", callback_data=f"adjust_chat_goal_{new_goal + 50}"),
                    InlineKeyboardButton("➕ 100", callback_data=f"adjust_chat_goal_{new_goal + 100}"),
                    InlineKeyboardButton("➕ 500", callback_data=f"adjust_chat_goal_{new_goal + 500}")
                )
                markup.row(
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_chat_goal_{new_goal}"),
                    InlineKeyboardButton("📝 Ввести вручную", callback_data="set_chat_goal_manual")
                )
                markup.row(
                    InlineKeyboardButton("◀️ Назад", callback_data="back_to_chat_goal_menu")
                )
                
                response = f"🎯 Настройка цели чата на {year} год\n\n"
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
            
            elif call.data.startswith("confirm_chat_goal_") or call.data.startswith("set_chat_goal_"):
                # Устанавливаем выбранную цель
                if call.data.startswith("confirm_chat_goal_"):
                    goal = float(call.data.split('_')[3])
                else:
                    goal = float(call.data.split('_')[3])
                
                # Создаем или обновляем челлендж чата
                challenge = Challenge.get_chat_challenge(chat_id, year)
                if challenge:
                    challenge.goal_km = goal
                    challenge.save()
                else:
                    challenge = Challenge(
                        title=f"Общая цель чата на {year} год",
                        goal_km=goal,
                        start_date=f"{year}-01-01",
                        end_date=f"{year}-12-31",
                        chat_id=chat_id,
                        is_system=False
                    )
                    challenge.save()
                
                # Получаем актуальную статистику
                total_km = challenge.get_total_progress()
                participants_count = challenge.get_participants_count()
                progress = (total_km / goal * 100) if goal > 0 else 0
                progress_bar = self._generate_progress_bar(progress)
                
                # Отправляем подтверждение
                if hasattr(call, 'id') and call.id:
                    self.bot.answer_callback_query(
                        call.id,
                        "✅ Цель чата успешно установлена"
                    )
                
                # Обновляем сообщение
                response = (
                    f"✅ Установлена общая цель чата на {year} год!\n\n"
                    f"🎯 Цель: {goal:.2f} км\n"
                    f"{progress_bar} {progress:.2f}%\n"
                    f"👥 Текущий прогресс: {total_km:.2f} км\n"
                    f"👤 Участников: {participants_count}\n\n"
                    f"Все участники чата автоматически участвуют в достижении цели."
                )
                
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton(
                        "🎯 Изменить цель",
                        callback_data="set_chat_goal_custom"
                    )
                )
                
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=response,
                    reply_markup=markup
                )
            
        except Exception as e:
            self.logger.error(f"Error in handle_set_chat_goal_callback: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            if hasattr(call, 'id') and call.id:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Произошла ошибка при установке цели"
                )

    def _generate_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Генерирует прогресс-бар"""
        filled = int(percentage / (100 / length))
        empty = length - filled
        return '▰' * filled + '▱' * empty

def register_handlers(bot):
    """Регистрирует обработчики целей чата"""
    handler = ChatGoalHandler(bot)
    handler.register() 