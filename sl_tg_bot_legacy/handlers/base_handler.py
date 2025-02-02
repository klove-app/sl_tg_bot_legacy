from telebot.types import Message
from database.logger import logger

class BaseHandler:
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger

    def register(self):
        """Регистрирует обработчики. Должен быть переопределен в дочерних классах"""
        raise NotImplementedError

    def log_message(self, message: Message, handler_name: str):
        """Логирует входящее сообщение"""
        self.logger.info(
            f"Handler {handler_name} received message: "
            f"text='{message.text}', "
            f"from_user={message.from_user.id}, "
            f"chat={message.chat.id}"
        ) 