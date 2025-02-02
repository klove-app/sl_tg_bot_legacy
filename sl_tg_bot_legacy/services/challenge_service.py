from database.models.challenge import Challenge
from database.models.user import User
from database.models.running_log import RunningLog
from database.base import get_db
from sqlalchemy import func, extract
from utils.formatters import round_km
from datetime import datetime, date
from database.logger import logger
import traceback

class ChallengeService:
    @staticmethod
    def get_active_challenges():
        """Получение списка активных челленджей"""
        db = next(get_db())
        try:
            current_date = datetime.now().date()
            
            # Получаем челленджи с количеством участников
            challenges = db.query(
                Challenge,
                func.count(Challenge.user_id).label('participants_count')
            ).filter(
                Challenge.end_date >= current_date
            ).group_by(
                Challenge.challenge_id
            ).order_by(
                Challenge.start_date
            ).all()
            
            return [{
                'id': c.Challenge.challenge_id,
                'title': c.Challenge.title,
                'goal_km': round_km(c.Challenge.goal_km),
                'start_date': c.Challenge.start_date,
                'end_date': c.Challenge.end_date,
                'description': c.Challenge.description,
                'created_by': c.Challenge.created_by,
                'participants_count': c.participants_count
            } for c in challenges]
        except Exception as e:
            logger.error(f"Error getting active challenges: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    @staticmethod
    def create_challenge(title, goal_km, start_date, end_date, description, created_by):
        return Challenge.create(title, goal_km, start_date, end_date, description, created_by)

    @staticmethod
    def get_challenge_stats(challenge_id):
        """Получение статистики по челленджу"""
        db = next(get_db())
        try:
            # Получаем челлендж
            challenge = db.query(Challenge).filter(
                Challenge.challenge_id == challenge_id
            ).first()
            
            if not challenge:
                return []
            
            # Получаем статистику участников
            stats = db.query(
                User.username,
                func.sum(RunningLog.km).label('total_km'),
                func.count(func.distinct(RunningLog.date_added)).label('active_days')
            ).join(
                Challenge, Challenge.user_id == User.user_id
            ).outerjoin(
                RunningLog, User.user_id == RunningLog.user_id
            ).filter(
                Challenge.challenge_id == challenge_id,
                RunningLog.date_added >= challenge.start_date,
                RunningLog.date_added <= challenge.end_date
            ).group_by(
                User.username
            ).order_by(
                func.sum(RunningLog.km).desc()
            ).all()
            
            return [{
                'username': s.username,
                'total_km': round_km(s.total_km or 0),
                'active_days': s.active_days
            } for s in stats]
        except Exception as e:
            logger.error(f"Error getting challenge stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    @staticmethod
    def get_user_challenges(user_id):
        """Получение челленджей пользователя"""
        db = next(get_db())
        try:
            # Получаем челленджи с общим пробегом
            challenges = db.query(
                Challenge,
                func.sum(RunningLog.km).label('total_km')
            ).outerjoin(
                RunningLog, 
                (RunningLog.user_id == Challenge.user_id) & 
                (RunningLog.date_added >= Challenge.start_date) & 
                (RunningLog.date_added <= Challenge.end_date)
            ).filter(
                Challenge.user_id == user_id
            ).group_by(
                Challenge.challenge_id
            ).order_by(
                Challenge.end_date.desc()
            ).all()
            
            return [{
                'challenge': c.Challenge,
                'total_km': round_km(c.total_km or 0)
            } for c in challenges]
        except Exception as e:
            logger.error(f"Error getting user challenges: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    @staticmethod
    def ensure_yearly_challenge(chat_id, year):
        """Создает или получает годовой челлендж чата"""
        # Проверяем, существует ли уже системный челлендж для этого чата и года
        challenge = Challenge.get_system_challenge(chat_id, year)
        
        if not challenge:
            # Создаем новый системный челлендж
            title = f"Годовая цель {year}"
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            challenge = Challenge.create(
                title=title,
                goal_km=0,  # Начальная цель
                start_date=start_date,
                end_date=end_date,
                chat_id=chat_id,
                is_system=True
            )
            
        return challenge

    @staticmethod
    def auto_join_user(user_id, chat_id):
        """Автоматически добавляет пользователя во все системные челленджи чата"""
        current_year = datetime.now().year
        # Присоединяем к текущему и следующему году
        for year in [current_year, current_year + 1]:
            challenge = ChallengeService.ensure_yearly_challenge(chat_id, year)
            if challenge:
                challenge.add_participant(user_id)

    @staticmethod
    def update_yearly_goal(chat_id, year, goal_km):
        """Обновляет цель годового челленджа"""
        challenge = ChallengeService.ensure_yearly_challenge(chat_id, year)
        if challenge:
            challenge.update_goal(goal_km)
            return True
        return False 