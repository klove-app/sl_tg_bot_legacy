from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
from handlers.base_handler import BaseHandler
from main import send_achievement_message
import traceback

class MessageHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики сообщений"""
        self.logger.info("Registering message handlers")
        
        self.bot.register_message_handler(
            self.handle_text,
            content_types=['text'],
            func=lambda message: (
                message.chat.type == 'private' or
                (self.bot.get_me().username and f"@{self.bot.get_me().username}" in message.text)
            )
        )
        
        # Регистрируем обработчик фотографий
        self.bot.register_message_handler(
            self.handle_photo_run,
            content_types=['photo'],
            func=lambda message: True
        )
        
        self.logger.info("Message handlers registered successfully")

    def handle_text(self, message: Message):
        """Обрабатывает текстовые сообщения"""
        self.log_message(message, "text")
        
        try:
            # Очищаем текст от упоминания бота
            text = message.text
            if self.bot.get_me().username:
                text = text.replace(f"@{self.bot.get_me().username}", "").strip()
            
            # Ищем первое число в тексте (поддерживаем и точку, и запятую)
            import re
            number_match = re.search(r'(\d+[.,]?\d*)', text)
            if not number_match:
                if message.chat.type == 'private':
                    self.bot.reply_to(
                        message,
                        "⚠️ *Не могу найти количество километров*\n\n"
                        "Отправьте сообщение в формате:\n"
                        "• `5.2` - просто километраж\n"
                        "• `5.2 Утренняя пробежка` - с описанием",
                        parse_mode='Markdown'
                    )
                return
                
            # Преобразуем найденное число в float
            km = float(number_match.group(1).replace(',', '.'))
            
            # Проверяем максимальную дистанцию
            if km > 100:
                self.bot.reply_to(message, "❌ Максимальная дистанция - 100 км")
                return
                
            # Получаем описание (всё после числа)
            description = text[number_match.end():].strip()
            
            # Добавляем запись о пробежке
            chat_id = str(message.chat.id) if message.chat.type != 'private' else None
            if RunningLog.add_entry(
                user_id=str(message.from_user.id),
                km=km,
                date_added=datetime.now().date(),
                notes=description if description else None,
                chat_id=chat_id
            ):
                # Получаем статистику пользователя
                user = User.get_by_id(str(message.from_user.id))
                total_km = RunningLog.get_user_total_km(str(message.from_user.id))
                
                # Получаем статистику за месяц и год
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                year_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year)
                month_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year, current_month)
                
                # Формируем сообщение со статистикой
                response = (
                    f"🎉 Новая пробежка записана!\n"
                    f"📍 {km:.1f} км\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                    
                    f"📊 Статистика {datetime.now().strftime('%B')}:\n"
                    f"🏃 {month_stats['runs_count']} пробежек\n"
                    f"📏 {month_stats['total_km']:.1f} км всего\n"
                    f"⌀ {month_stats['avg_km']:.1f} км в среднем\n\n"
                    
                    f"📈 Статистика {current_year}:\n"
                    f"🏃 {year_stats['runs_count']} пробежек\n"
                    f"📏 {year_stats['total_km']:.1f} км всего\n"
                    f"⌀ {year_stats['avg_km']:.1f} км в среднем"
                )
                
                # Добавляем информацию о годовой цели
                if user and user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                    remaining = user.goal_km - total_km
                    response += (
                        f"\n\n🎯 Годовая цель:\n"
                        f"🎪 {user.goal_km:.0f} км\n"
                        f"▸ {progress_bar} {progress:.1f}%\n"
                        f"📍 Осталось: {remaining:.1f} км"
                    )
                
                # Добавляем мотивационное сообщение
                if km >= 10:
                    response += "\n\n🔥 Отличная длительная пробежка!"
                elif km >= 5:
                    response += "\n\n💪 Хорошая тренировка!"
                else:
                    response += "\n\n👍 Так держать!"
                
                # Для пробежек от 5 км генерируем изображение
                if km >= 5:
                    try:
                        username = message.from_user.username or message.from_user.first_name
                        date = datetime.now().strftime('%d.%m.%Y')
                        from main import generate_achievement_image
                        image_data = generate_achievement_image(km, username, date)
                        if image_data:
                            from io import BytesIO
                            photo = BytesIO(image_data)
                            photo.name = 'achievement.png'
                            self.bot.send_photo(
                                message.chat.id,
                                photo,
                                caption=response,
                                parse_mode='Markdown',
                                reply_to_message_id=message.message_id
                            )
                        else:
                            self.bot.reply_to(message, response, parse_mode='Markdown')
                    except Exception as e:
                        self.logger.error(f"Ошибка при генерации изображения: {e}")
                        self.bot.reply_to(message, response, parse_mode='Markdown')
                else:
                    self.bot.reply_to(message, response, parse_mode='Markdown')
                
                self.logger.info(f"Logged run: {km}km for user {message.from_user.id}")
            else:
                self.bot.reply_to(message, "❌ Не удалось сохранить пробежку")
                
        except ValueError as e:
            self.logger.error(f"Error parsing message: {e}")
            if message.chat.type == 'private':
                self.bot.reply_to(
                    message,
                    "⚠️ *Некорректный формат*\n\n"
                    "Отправьте сообщение в формате:\n"
                    "• `5.2` - просто километраж\n"
                    "• `5.2 Утренняя пробежка` - с описанием",
                    parse_mode='Markdown'
                )

    def handle_photo_run(self, message):
        """Обработчик фотографий с подписью"""
        self.logger.info(f"Processing photo message with caption: {message.caption}")
        self.logger.info(f"Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
        
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
            self.logger.warning("No caption provided with photo")
            self.bot.reply_to(
                message,
                "⚠️ *Добавьте подпись с километражем*\n\n"
                "Пример: `5.2` или `5.2 Утренняя пробежка`",
                parse_mode='Markdown'
            )
            return
            
        try:
            # Извлекаем первое число из подписи, поддерживая целые и дробные числа
            first_word = message.caption.split()[0]
            # Пробуем сначала преобразовать как есть (для целых чисел)
            try:
                km = float(first_word)
            except ValueError:
                # Если не получилось, пробуем заменить запятую на точку (для дробных)
                km = float(first_word.replace(',', '.'))
            
            self.logger.info(f"Extracted distance from caption: {km} km")
            
            if km <= 0:
                self.logger.warning(f"Invalid distance: {km} km")
                self.bot.reply_to(
                    message,
                    "⚠️ *Некорректная дистанция*\n\n"
                    "Пожалуйста, укажите положительное число километров",
                    parse_mode='Markdown'
                )
                return
                
            user_id = str(message.from_user.id)
            chat_id = str(message.chat.id)
            chat_type = message.chat.type
            
            self.logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Chat Type: {chat_type}")
            
            # Получаем или создаем пользователя
            user = User.get_by_id(user_id)
            self.logger.debug(f"Found user: {user}")
            
            if not user:
                username = message.from_user.username or message.from_user.first_name
                self.logger.info(f"Creating new user: {username}")
                user = User.create(user_id=user_id, username=username)
                self.logger.info(f"Created new user: {username} ({user_id})")
            
            # Добавляем запись о пробежке
            self.logger.info(f"Adding run entry with photo: {km} km")
            success = RunningLog.add_entry(
                user_id=user_id,
                km=km,
                date_added=datetime.now().date(),
                notes=message.caption,
                chat_id=chat_id,
                chat_type=chat_type
            )
            
            if success:
                self.logger.info("Run entry with photo added successfully")
                # Получаем статистику
                total_km = RunningLog.get_user_total_km(user_id)
                self.logger.debug(f"Total km: {total_km}")
                
                # Получаем статистику за месяц и год
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                year_stats = RunningLog.get_user_stats(user_id, current_year)
                month_stats = RunningLog.get_user_stats(user_id, current_year, current_month)
                
                # Формируем сообщение со статистикой
                response = (
                    f"🎉 Новая пробежка записана!\n"
                    f"📍 {km:.1f} км\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                    
                    f"📊 Статистика {datetime.now().strftime('%B')}:\n"
                    f"🏃 {month_stats['runs_count']} пробежек\n"
                    f"📏 {month_stats['total_km']:.1f} км всего\n"
                    f"⌀ {month_stats['avg_km']:.1f} км в среднем\n\n"
                    
                    f"📈 Статистика {current_year}:\n"
                    f"🏃 {year_stats['runs_count']} пробежек\n"
                    f"📏 {year_stats['total_km']:.1f} км всего\n"
                    f"⌀ {year_stats['avg_km']:.1f} км в среднем"
                )
                
                # Добавляем информацию о годовой цели
                if user and user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                    remaining = user.goal_km - total_km
                    response += (
                        f"\n\n🎯 Годовая цель:\n"
                        f"🎪 {user.goal_km:.0f} км\n"
                        f"▸ {progress_bar} {progress:.1f}%\n"
                        f"📍 Осталось: {remaining:.1f} км"
                    )
                
                # Добавляем мотивационное сообщение
                if km >= 10:
                    response += "\n\n🔥 Отличная длительная пробежка!"
                elif km >= 5:
                    response += "\n\n💪 Хорошая тренировка!"
                else:
                    response += "\n\n👍 Так держать!"
                
                # Для пробежек от 5 км генерируем изображение
                if km >= 5:
                    try:
                        username = message.from_user.username or message.from_user.first_name
                        date = datetime.now().strftime('%d.%m.%Y')
                        from main import generate_achievement_image
                        image_data = generate_achievement_image(km, username, date)
                        if image_data:
                            from io import BytesIO
                            photo = BytesIO(image_data)
                            photo.name = 'achievement.png'
                            self.bot.send_photo(
                                message.chat.id,
                                photo,
                                caption=response,
                                parse_mode='Markdown',
                                reply_to_message_id=message.message_id
                            )
                        else:
                            self.bot.reply_to(message, response, parse_mode='Markdown')
                    except Exception as e:
                        self.logger.error(f"Ошибка при генерации изображения: {e}")
                        self.bot.reply_to(message, response, parse_mode='Markdown')
                else:
                    self.bot.reply_to(message, response, parse_mode='Markdown')
                
                self.logger.info(f"Logged run with photo: {km}km for user {user_id}")
            else:
                self.logger.error(f"Failed to save run with photo for user {user_id}")
                error_message = (
                    "⚠️ *Не удалось сохранить пробежку*\n\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору"
                )
                self.bot.reply_to(message, error_message, parse_mode='Markdown')
            return
                
        except ValueError:
            self.logger.warning(f"Invalid caption format: {message.caption}")
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

def register_handlers(bot):
    """Регистрирует обработчики сообщений"""
    handler = MessageHandler(bot)
    handler.register() 