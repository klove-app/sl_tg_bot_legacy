from telebot.types import Message
from database.models.running_log import RunningLog
from database.models.challenge import Challenge
from handlers.base_handler import BaseHandler
from datetime import datetime

class ResetHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики сброса данных"""
        self.logger.info("Registering reset handlers")
        
        self.bot.register_message_handler(
            self.handle_reset,
            func=lambda message: any(
                phrase in message.text.lower() 
                for phrase in ["обнулить с", "сбросить с"]
            )
        )
        
        self.logger.info("Reset handlers registered successfully")
        
    def handle_reset(self, message: Message):
        """Обрабатывает запрос на сброс данных"""
        try:
            # Извлекаем год из сообщения
            text = message.text.lower()
            year = None
            for word in text.split():
                if word.isdigit() and len(word) == 2:  # Проверяем, что это двузначное число
                    year = int("20" + word)  # Преобразуем "23" в "2023"
                    break
            
            if not year:
                self.bot.reply_to(message, "❌ Не удалось определить год для сброса. Укажите год в формате '23' или '24'")
                return
                
            if year < datetime.now().year:
                self.bot.reply_to(message, "❌ Нельзя сбросить данные для прошедшего года")
                return
                
            user_id = str(message.from_user.id)
            
            # Удаляем цели пользователя для указанного года
            challenges = Challenge.get_all_user_challenges(user_id)
            for challenge in challenges:
                if challenge.start_date.startswith(str(year)):
                    challenge.delete()
            
            # Создаем новую цель на указанный год
            new_challenge = Challenge(
                title=f"Личная цель на {year} год",
                goal_km=0,  # Начальная цель 0 км
                start_date=f"{year}-01-01",
                end_date=f"{year}-12-31",
                chat_id=str(message.chat.id),
                is_system=True,
                user_id=user_id
            )
            new_challenge.save()
            
            self.bot.reply_to(
                message,
                f"✅ Данные успешно сброшены для {year} года!\n\n"
                f"Используйте /setgoal чтобы установить новую цель."
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_reset: {e}")
            self.bot.reply_to(message, "❌ Произошла ошибка при сбросе данных") 