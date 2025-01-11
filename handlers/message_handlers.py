from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
from handlers.base_handler import BaseHandler
from main import generate_achievement_image, add_watermark
from io import BytesIO
import traceback
import re

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
        """Обработчик текстовых сообщений"""
        self.logger.info(f"Processing message: {message.text}")
        self.logger.info(f"Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
        
        # Определяем username и date в начале функции
        username = message.from_user.username or message.from_user.first_name
        if not username:
            username = "Anonymous"
            self.logger.info("Username not available, using 'Anonymous'")
        date = datetime.now().strftime('%d.%m.%Y')
        self.logger.info(f"Username determined: {username}")
        
        try:
            # Очищаем текст от упоминания бота
            text = message.text
            if self.bot.get_me().username:
                text = text.replace(f"@{self.bot.get_me().username}", "").strip()
            
            # Ищем первое число в тексте (поддерживаем и точку, и запятую)
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
            self.logger.info("=== Before adding run entry ===")
            if RunningLog.add_entry(
                user_id=str(message.from_user.id),
                km=km,
                date_added=datetime.now().date(),
                notes=description if description else None,
                chat_id=chat_id
            ):
                self.logger.info("=== Run entry added successfully, preparing response ===")
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
                
                self.logger.info("=== Starting image generation block ===")
                self.logger.info(f"Message from user: {message.from_user.id}")
                self.logger.info(f"Distance: {km} km")
                self.logger.info("Response message prepared, attempting image generation")
                
                try:
                    self.logger.info("Preparing to generate achievement image")
                    self.logger.info(f"Calling generate_achievement_image with: km={km}, username={username}, date={date}")
                    image_data = generate_achievement_image(km, username, date)
                    self.logger.info("Image generation call completed")
                    
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
                    self.logger.error(f"Error in image generation/sending: {e}")
                    self.logger.error(traceback.format_exc())
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
            self.logger.info(f"Adding run entry: {km} km")
            
            # Определяем username до генерации изображения
            username = message.from_user.username or message.from_user.first_name
            if not username:
                username = "Anonymous"
            date = datetime.now().strftime('%d.%m.%Y')
            
            self.logger.info(f"Username: {username}, Date: {date}")
            
            # Получаем статистику за месяц и год
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            year_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year)
            month_stats = RunningLog.get_user_stats(str(message.from_user.id), current_year, current_month)
            
            # Формируем сообщение со статистикой
            response = (
                f"🎉 Пробежка с фото записана!\n"
                f"📍 {km:.1f} км\n"
                f"📅 {date}\n\n"
                
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
            if user.goal_km and user.goal_km > 0:
                total_km = RunningLog.get_user_total_km(user_id)
                progress = (total_km / user.goal_km * 100)
                progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                remaining = user.goal_km - total_km
                response += (
                    f"\n\n🎯 Годовая цель:\n"
                    f"🎪 {user.goal_km:.0f} км\n"
                    f"▸ {progress_bar} {progress:.1f}%\n"
                    f"📍 Осталось: {remaining:.1f} км"
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
            
            # Генерируем изображение
            image_data = generate_achievement_image(km, username, date)
            
            # Добавляем запись в базу данных
            RunningLog.add_run(user_id, km, chat_id, chat_type)
            
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
                
            self.logger.info(f"Logged run with photo: {km}km for user {user_id}")
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