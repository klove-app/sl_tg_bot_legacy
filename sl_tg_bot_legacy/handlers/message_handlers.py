from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
from handlers.base_handler import BaseHandler
from main import generate_achievement_image, add_watermark
from io import BytesIO
import traceback
import re
from config import config as cfg

class MessageHandler(BaseHandler):
    def _get_username(self, message):
        """Безопасное получение имени пользователя"""
        try:
            username = message.from_user.username
            if not username:
                username = message.from_user.first_name
            if not username:
                username = f"User{message.from_user.id}"
            self.logger.info(f"Retrieved username: {username}")
            return username
        except Exception as e:
            self.logger.error(f"Error getting username: {e}")
            return f"User{message.from_user.id}"

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
        """Обработчик текстовых сообщений"""
        try:
            self.logger.info("=== Starting handle_text ===")
            self.logger.info(f"Processing message: {message.text}")
            self.logger.info(f"Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
            
            # Проверяем, что сообщение адресовано боту
            is_bot_mentioned = False
            if message.reply_to_message and message.reply_to_message.from_user.id == self.bot.get_me().id:
                is_bot_mentioned = True
                self.logger.info("Bot mentioned via reply")
            elif self.bot.get_me().username and f"@{self.bot.get_me().username}" in message.text:
                is_bot_mentioned = True
                self.logger.info("Bot mentioned via @username")
            elif message.chat.type == 'private':
                is_bot_mentioned = True
                self.logger.info("Private chat message")
                
            # Если сообщение не адресовано боту - игнорируем
            if not is_bot_mentioned:
                self.logger.info("Message not addressed to bot, ignoring")
                return
            
            # Определяем username в начале функции
            username = self._get_username(message)
            date = datetime.now().strftime('%d.%m.%Y')
            self.logger.info(f"Username determined: {username}")
            
            # Очищаем текст от упоминания бота
            text = message.text
            if self.bot.get_me().username:
                text = text.replace(f"@{self.bot.get_me().username}", "").strip()
            self.logger.info(f"Cleaned text: {text}")
            
            # Ищем первое число в тексте
            number_match = re.search(r'(\d+[.,]?\d*)', text)
            if not number_match:
                self.logger.info("No distance found in message")
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
            self.logger.info(f"Extracted distance: {km} km")
            
            # Проверяем максимальную дистанцию
            if km > 100:
                self.logger.info(f"Distance {km} km exceeds maximum limit")
                self.bot.reply_to(message, "❌ Максимальная дистанция - 100 км")
                return
                
            # Получаем описание
            description = text[number_match.end():].strip()
            self.logger.info(f"Description: {description}")
            
            # Получаем статистику
            self.logger.info("=== Getting statistics ===")
            user = User.get_by_id(str(message.from_user.id))
            total_km = RunningLog.get_user_total_km(str(message.from_user.id))
            
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            year_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year)
            month_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year, current_month)
            
            self.logger.info("=== Preparing response message ===")
            # Формируем сообщение со статистикой
            response = (
                f"🎉 Новая пробежка записана!\n"
                f"📍 {km:.2f} км\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                
                f"📊 Статистика {datetime.now().strftime('%B')}:\n"
                f"🏃 {month_stats['runs_count']} пробежек\n"
                f"📏 {month_stats['total_km']:.2f} км всего\n"
                f"⌀ {month_stats['avg_km']:.2f} км в среднем\n\n"
                
                f"📈 Статистика {current_year}:\n"
                f"🏃 {year_stats['runs_count']} пробежек\n"
                f"📏 {year_stats['total_km']:.2f} км всего\n"
                f"⌀ {year_stats['avg_km']:.2f} км в среднем"
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
                    f"📍 Осталось: {remaining:.2f} км"
                )
            
            # Добавляем мотивационное сообщение
            if km >= 10:
                response += "\n\n🔥 Отличная длительная пробежка!"
            elif km >= 5:
                response += "\n\n💪 Хорошая тренировка!"
            else:
                response += "\n\n👍 Так держать!"
            
            # Генерируем изображение для любой дистанции
            self.logger.info("=== Starting image generation ===")
            self.logger.info(f"Parameters: km={km}, username={username}, date={date}")
            self.logger.info("Attempting to generate image...")
            
            try:
                self.logger.info("Before calling generate_achievement_image")
                self.logger.info(f"API settings: host={cfg.STABILITY_API_HOST}, key={'present' if cfg.STABILITY_API_KEY else 'missing'}")
                image_data = generate_achievement_image(km, username, date)
                self.logger.info(f"After calling generate_achievement_image, got data: {'yes' if image_data else 'no'}")
                
                if image_data:
                    self.logger.info("Image data received, creating BytesIO")
                    photo = BytesIO(image_data)
                    photo.name = 'achievement.png'
                    self.bot.send_photo(
                        message.chat.id,
                        photo,
                        caption=response,
                        parse_mode='Markdown',
                        reply_to_message_id=message.message_id
                    )
                    self.logger.info("Photo sent successfully")
                else:
                    self.logger.error("Image data is None")
                    self.bot.reply_to(message, response, parse_mode='Markdown')
            except Exception as e:
                self.logger.error(f"Error in image generation/sending: {str(e)}")
                self.logger.error("Full error:")
                self.logger.error(traceback.format_exc())
                self.bot.reply_to(message, response, parse_mode='Markdown')
            
            # Сохраняем запись о пробежке после отправки сообщения
            self.logger.info("=== Saving run entry ===")
            chat_id = str(message.chat.id) if message.chat.type != 'private' else None
            if RunningLog.add_entry(
                user_id=str(message.from_user.id),
                km=km,
                date_added=datetime.now().date(),
                notes=description if description else None,
                chat_id=chat_id
            ):
                self.logger.info(f"Run entry saved: {km}km for user {message.from_user.id}")
            else:
                self.logger.error("Failed to save run entry")
                self.bot.reply_to(message, "❌ Не удалось сохранить пробежку")
                
        except Exception as e:
            self.logger.error(f"Error in handle_text: {e}")
            self.logger.error(traceback.format_exc())
            if message.chat.type == 'private':
                self.bot.reply_to(
                    message,
                    "⚠️ *Произошла ошибка*\n\n"
                    "Пожалуйста, попробуйте позже или обратитесь к администратору",
                    parse_mode='Markdown'
                )

    def handle_photo_run(self, message):
        """Обработчик фотографий с подписью"""
        self.logger.info(f"Processing photo message with caption: {message.caption}")
        self.logger.info(f"Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
        
        # Определяем username в начале функции
        username = self._get_username(message)
        date = datetime.now().strftime('%d.%m.%Y')
        self.logger.info(f"Username determined: {username}")
        
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
            # Сначала заменяем запятую на точку (для дробных)
            first_word = first_word.replace(',', '.')
            # Затем пробуем преобразовать в число
            try:
                km = float(first_word)
            except ValueError:
                raise ValueError("Не удалось преобразовать строку в число")
            
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
            
            # Получаем статистику за месяц и год
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            year_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year)
            month_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year, current_month)
            
            # Формируем сообщение со статистикой
            response = (
                f"🎉 Пробежка с фото записана!\n"
                f"📍 {km:.2f} км\n"
                f"📅 {date}\n\n"
                
                f"📊 Статистика {datetime.now().strftime('%B')}:\n"
                f"🏃 {month_stats['runs_count']} пробежек\n"
                f"📏 {month_stats['total_km']:.2f} км всего\n"
                f"⌀ {month_stats['avg_km']:.2f} км в среднем\n\n"
                
                f"📈 Статистика {current_year}:\n"
                f"🏃 {year_stats['runs_count']} пробежек\n"
                f"📏 {year_stats['total_km']:.2f} км всего\n"
                f"⌀ {year_stats['avg_km']:.2f} км в среднем"
            )
            
            # Добавляем информацию о годовой цели
            if user.goal_km and user.goal_km > 0:
                total_km = RunningLog.get_user_total_km(user_id)
                progress = (total_km / user.goal_km * 100)
                progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                remaining = user.goal_km - total_km
                response += (
                    f"\n\n🎯 Годовая цель:\n"
                    f"🎪 {user.goal_km:.0f} км\n"
                    f"▸ {progress_bar} {progress:.1f}%\n"
                    f"📍 Осталось: {remaining:.2f} км"
                )
            else:
                response += "\n\n💡 Установите годовую цель командой /goal"
            
            # Добавляем мотивационное сообщение
            if km >= 10:
                response += "\n\n🔥 Отличная длительная пробежка!"
            elif km >= 5:
                response += "\n\n💪 Хорошая тренировка!"
            else:
                response += "\n\n👍 Так держать!"
            
            # Добавляем водяные знаки на фото пользователя
            self.logger.info("=== Adding watermark to user's photo ===")
            self.logger.info(f"Parameters: km={km}, username={username}, date={date}")
            
            try:
                # Получаем фото в максимальном размере
                file_info = self.bot.get_file(message.photo[-1].file_id)
                downloaded_file = self.bot.download_file(file_info.file_path)
                
                self.logger.info("Photo downloaded successfully")
                
                # Добавляем водяные знаки
                image_data = add_watermark(
                    downloaded_file,
                    f"{username} • {date}",  # Информация о пробежке
                    "Бег: свои люди",        # Название чата
                    f"{km:.2f} км",          # Километраж
                    km                       # Для позиционирования
                )
                self.logger.info("Watermark added successfully")
                
                if image_data:
                    self.logger.info("Image data received, creating BytesIO")
                    photo = BytesIO(image_data)
                    photo.name = 'achievement.png'
                    self.logger.info("Sending photo with caption")
                    self.bot.send_photo(
                        message.chat.id,
                        photo,
                        caption=response,
                        parse_mode='Markdown',
                        reply_to_message_id=message.message_id
                    )
                    self.logger.info("Photo sent successfully")
                else:
                    self.logger.error("Image data is None")
                    self.bot.reply_to(message, response, parse_mode='Markdown')
            except Exception as e:
                self.logger.error(f"Error in image processing/sending: {str(e)}")
                self.logger.error("Full error:")
                self.logger.error(traceback.format_exc())
                self.bot.reply_to(message, response, parse_mode='Markdown')
            
            # Сохраняем запись о пробежке после отправки сообщения
            if RunningLog.add_entry(
                user_id=user_id,
                km=km,
                date_added=datetime.now().date(),
                notes=message.caption,
                chat_id=chat_id,
                chat_type=chat_type
            ):
                self.logger.info(f"Logged run with photo: {km}km for user {user_id}")
            else:
                error_message = (
                    "⚠️ *Не удалось сохранить пробежку*\n\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору"
                )
                self.bot.reply_to(message, error_message, parse_mode='Markdown')
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
            self.logger.error(traceback.format_exc())
            error_message = (
                "😔 *Произошла ошибка*\n\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору"
            )
            self.bot.reply_to(message, error_message, parse_mode='Markdown')

def register_handlers(bot):
    """Регистрирует обработчики сообщений"""
    handler = MessageHandler(bot)
    handler.register() 