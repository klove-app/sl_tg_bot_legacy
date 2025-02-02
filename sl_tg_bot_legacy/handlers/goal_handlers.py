from telebot.types import Message
from database.models.user import User
from database.models.running_log import RunningLog
import traceback
from handlers.base_handler import BaseHandler

class GoalHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики целей"""
        self.logger.info("Registering goal handlers")
        
        # Регистрируем обработчики команд напрямую
        self.bot.register_message_handler(
            self.handle_setgoal,
            commands=['setgoal']
        )
        
        self.logger.info("Goal handlers registered successfully")

    def handle_setgoal(self, message: Message):
        """Устанавливает годовую цель"""
        self.log_message(message, "setgoal")
        try:
            args = message.text.split()
            if len(args) != 2:
                self.bot.reply_to(message, "❌ Укажите цель в километрах\nПример: /setgoal 1000")
                return

            try:
                goal_km = float(args[1].replace(',', '.'))
            except ValueError:
                self.bot.reply_to(message, "❌ Неверный формат числа")
                return

            if goal_km <= 0:
                self.bot.reply_to(message, "❌ Цель должна быть больше нуля")
                return

            user_id = str(message.from_user.id)
            self.logger.info(f"Getting user {user_id} from database")
            user = User.get_by_id(user_id)
            if not user:
                username = message.from_user.username or message.from_user.first_name
                user = User.create(user_id=user_id, username=username)
                self.logger.info(f"Created new user: {username} ({user_id})")

            user.goal_km = goal_km
            user.save()
            self.logger.info(f"Updated goal for user {user_id} to {goal_km} km")

            total_km = RunningLog.get_user_total_km(user_id)
            progress = (total_km / goal_km * 100)

            response = f"🎯 Установлена цель на год: {goal_km:.2f} км\n"
            response += f"📊 Текущий прогресс: {total_km:.2f} км ({progress:.2f}%)"

            self.logger.info(f"Sending response: {response}")
            self.bot.reply_to(message, response)
            self.logger.info(f"Set goal {goal_km}km for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error in handle_setgoal: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при установке цели")

def register_handlers(bot):
    """Регистрирует обработчики целей"""
    handler = GoalHandler(bot)
    handler.register() 