from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
from datetime import datetime
from handlers.base_handler import BaseHandler

class MessageHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики сообщений"""
        self.logger.info("Registering message handlers")
        
        self.bot.register_message_handler(
            self.handle_text,
            content_types=['text'],
            func=lambda message: message.reply_to_message is not None
        )
        
        self.logger.info("Message handlers registered successfully")

    def handle_text(self, message: Message):
        """Обрабатывает текстовые сообщения"""
        self.log_message(message, "text")
        
        # Проверяем, является ли сообщение ответом на сообщение бота
        if message.reply_to_message and message.reply_to_message.from_user.username == self.bot.get_me().username:
            # Проверяем, есть ли обращение к боту в тексте
            bot_mention = f"@{self.bot.get_me().username}"
            if bot_mention not in message.text:
                return
                
            try:
                # Пытаемся преобразовать текст в число
                km = float(message.text.replace(bot_mention, "").strip())
                
                # Проверяем максимальную дистанцию
                if km > 100:
                    self.bot.reply_to(message, "❌ Максимальная дистанция - 100 км")
                    return
                
                # Добавляем запись о пробежке
                chat_id = str(message.chat.id) if message.chat.type != 'private' else None
                if RunningLog.add_entry(
                    user_id=str(message.from_user.id),
                    km=km,
                    date_added=datetime.now().date(),
                    chat_id=chat_id
                ):
                    # Получаем статистику пользователя
                    user = User.get_by_id(str(message.from_user.id))
                    total_km = RunningLog.get_user_total_km(str(message.from_user.id))
                    
                    response = f"✅ Записана пробежка {km:.2f} км!\n"
                    if user and user.goal_km > 0:
                        progress = (total_km / user.goal_km * 100)
                        response += f"📊 Прогресс: {total_km:.2f} из {user.goal_km:.2f} км ({progress:.2f}%)"
                    
                    self.bot.reply_to(message, response)
                    self.logger.info(f"Logged run: {km}km for user {message.from_user.id}")
                else:
                    self.bot.reply_to(message, "❌ Не удалось сохранить пробежку")
                    
            except ValueError:
                # Если не удалось преобразовать текст в число, игнорируем сообщение
                pass

def register_handlers(bot):
    """Регистрирует обработчики сообщений"""
    handler = MessageHandler(bot)
    handler.register() 