from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
from handlers.base_handler import BaseHandler
from main import send_achievement_message

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
                
                response = f"✅ Записана пробежка {km:.2f} км"
                if description:
                    response += f"\n📝 {description}"
                    
                if user and user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    response += f"\n\n📊 Прогресс: {total_km:.2f} из {user.goal_km:.2f} км ({progress:.2f}%)"
                
                self.bot.reply_to(message, response)
                
                # Генерируем изображение для достижения
                if km >= 5:  # Генерируем только для пробежек от 5 км
                    try:
                        username = message.from_user.username or message.from_user.first_name
                        date = datetime.now().strftime('%d.%m.%Y')
                        send_achievement_message(message, km)
                    except Exception as e:
                        self.logger.error(f"Ошибка при генерации изображения: {e}")
                
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

def register_handlers(bot):
    """Регистрирует обработчики сообщений"""
    handler = MessageHandler(bot)
    handler.register() 