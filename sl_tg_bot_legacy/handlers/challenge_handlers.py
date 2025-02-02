from services.challenge_service import ChallengeService
from datetime import datetime

def register_handlers(bot):
    @bot.message_handler(commands=['createchallenge'])
    def create_challenge(message):
        try:
            parts = message.text.split(maxsplit=5)
            if len(parts) < 5:
                bot.reply_to(message, 
                    "Использование: /createchallenge название км ГГГГ-ММ-ДД ГГГГ-ММ-ДД описание\n"
                    "Пример: /createchallenge Марафон 42.2 2024-03-01 2024-03-31 Марафон за месяц")
                return

            title = parts[1]
            goal_km = float(parts[2])
            start_date = datetime.strptime(parts[3], '%Y-%m-%d').date()
            end_date = datetime.strptime(parts[4], '%Y-%m-%d').date()
            description = parts[5] if len(parts) > 5 else ""
            
            if start_date > end_date:
                bot.reply_to(message, "Дата начала не может быть позже даты окончания")
                return
                
            user_id = str(message.from_user.id)
            
            challenge = ChallengeService.create_challenge(
                title, goal_km, start_date, end_date, description, user_id
            )
            
            response = f"Челлендж '{title}' успешно создан!\n"
            response += f"ID: {challenge.challenge_id}\n"
            response += f"Цель: {challenge.goal_km} км\n"
            response += f"Период: {start_date} - {end_date}\n"
            response += f"Описание: {description}"
            
            bot.reply_to(message, response)
            
        except ValueError:
            bot.reply_to(message, 
                "Ошибка в формате данных. Проверьте правильность дат и километража.")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка: {str(e)}")

    @bot.message_handler(commands=['challenges'])
    def list_challenges(message):
        try:
            challenges = ChallengeService.get_active_challenges()
            
            if not challenges:
                bot.reply_to(message, "Активных челленджей не найдено")
                return
                
            response = "🏃‍♂️ Список активных челленджей:\n\n"
            
            for challenge in challenges:
                response += f"🎯 {challenge.title} (ID: {challenge.challenge_id})\n"
                response += f"Цель: {challenge.goal_km} км\n"
                response += f"Период: {challenge.start_date} - {challenge.end_date}\n"
                if challenge.description:
                    response += f"Описание: {challenge.description}\n"
                response += f"👉 Присоединиться: /joinchallenge {challenge.challenge_id}\n\n"
            
            bot.reply_to(message, response)
            
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка: {str(e)}")

    @bot.message_handler(commands=['challengestats'])
    def challenge_stats(message):
        try:
            parts = message.text.split()
            if len(parts) < 2:
                bot.reply_to(message, "Использование: /challengestats [ID челленджа]")
                return
                
            challenge_id = int(parts[1])
            stats = ChallengeService.get_challenge_stats(challenge_id)
            
            if not stats:
                bot.reply_to(message, "Статистика не найдена или челлендж не существует")
                return
                
            response = "📊 Статистика участников:\n\n"
            
            for idx, participant in enumerate(stats, 1):
                response += f"{idx}. {participant['username']}:\n"
                response += f"   Пройдено: {participant['total_km']} км\n"
                response += f"   Активных дней: {participant['active_days']}\n\n"
            
            bot.reply_to(message, response)
            
        except ValueError:
            bot.reply_to(message, "Некорректный ID челленджа")
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка: {str(e)}") 