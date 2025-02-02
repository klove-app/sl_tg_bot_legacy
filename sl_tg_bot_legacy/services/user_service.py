from database.models.user import User
from database.models.running_log import RunningLog
from database.base import get_db
from sqlalchemy import func, extract
from utils.formatters import round_km
from datetime import datetime
from services.challenge_service import ChallengeService
from database.logger import logger
import traceback

class UserService:
    @staticmethod
    def add_run(user_id, km, notes=None, date=None):
        """Добавляет новую пробежку для пользователя"""
        db = next(get_db())
        try:
            user = User.get_by_id(user_id)
            if not user:
                raise ValueError("Пользователь не найден")

            if date is None:
                date = datetime.now().date()

            # Добавляем запись о пробежке
            success = RunningLog.add_entry(user_id, km, date, notes)
            if not success:
                raise ValueError("Не удалось добавить запись о пробежке")

            # Обновляем прогресс пользователя
            total_km = RunningLog.get_user_total_km(user_id)
            user.yearly_progress = total_km
            user.save()

            return round_km(km)
        except Exception as e:
            logger.error(f"Error adding run: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        finally:
            db.close()

    @staticmethod
    def get_user_stats(user_id):
        """Получает статистику пользователя"""
        db = next(get_db())
        try:
            user = User.get_by_id(user_id)
            if not user:
                return None
                
            total_km = RunningLog.get_user_total_km(user_id)
            completion = round_km((total_km / user.yearly_goal * 100) if user.yearly_goal > 0 else 0)
            
            # Получаем последние записи
            recent_runs = RunningLog.get_recent_runs(user_id, limit=5)
            
            return {
                'username': user.username,
                'yearly_goal': user.yearly_goal,
                'total_km': total_km,
                'completion_percentage': completion,
                'recent_runs': recent_runs
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
        finally:
            db.close()

    @staticmethod
    def register_user(message):
        """Регистрация нового пользователя"""
        db = next(get_db())
        try:
            user_id = str(message.from_user.id)
            username = message.from_user.username or message.from_user.first_name
            
            user = User.create(user_id, username)
            
            # Если сообщение из чата, добавляем пользователя в системные челленджи
            if message.chat.type != 'private':
                ChallengeService.auto_join_user(user_id, str(message.chat.id))
            
            return user
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        finally:
            db.close() 