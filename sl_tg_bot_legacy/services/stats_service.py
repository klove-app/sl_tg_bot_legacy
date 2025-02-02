from database.base import get_db
from database.models.user import User
from database.models.running_log import RunningLog
from sqlalchemy import func, extract
from utils.formatters import round_km
from datetime import datetime
from functools import lru_cache
from database.logger import logger
import traceback

class StatsService:
    @staticmethod
    @lru_cache(maxsize=100)
    def get_user_stats(user_id):
        """Получение статистики пользователя"""
        db = next(get_db())
        try:
            current_year = datetime.now().year
            
            # Получаем данные пользователя
            result = db.query(
                User.yearly_goal,
                func.sum(RunningLog.km).label('total_km'),
                func.count(func.distinct(RunningLog.date_added)).label('activity_count')
            ).outerjoin(
                RunningLog,
                (User.user_id == RunningLog.user_id) &
                (extract('year', RunningLog.date_added) == current_year)
            ).filter(
                User.user_id == user_id
            ).group_by(
                User.user_id,
                User.yearly_goal
            ).first()
            
            if not result:
                return None
            
            yearly_goal = round_km(result.yearly_goal or 0)
            total_km = round_km(result.total_km or 0)
            activity_count = result.activity_count or 0
            
            # Расчет процента выполнения
            completion_percentage = round_km((total_km / yearly_goal * 100) if yearly_goal > 0 else 0)
            
            return {
                'yearly_goal': yearly_goal,
                'total_km': total_km,
                'activity_count': activity_count,
                'completion_percentage': completion_percentage
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
        finally:
            db.close()

    @staticmethod
    def invalidate_cache(user_id):
        """Инвалидация кэша при обновлении данных"""
        StatsService.get_user_stats.cache_clear()

    @staticmethod
    def get_leaderboard():
        """Получение таблицы лидеров"""
        db = next(get_db())
        try:
            current_year = datetime.now().year
            
            results = db.query(
                User.username,
                User.yearly_goal,
                func.sum(RunningLog.km).label('total_km')
            ).outerjoin(
                RunningLog,
                (User.user_id == RunningLog.user_id) &
                (extract('year', RunningLog.date_added) == current_year)
            ).group_by(
                User.username,
                User.yearly_goal
            ).having(
                User.yearly_goal > 0
            ).order_by(
                func.sum(RunningLog.km).desc()
            ).all()
            
            return [{
                'username': result.username,
                'yearly_goal': round_km(result.yearly_goal),
                'total_km': round_km(result.total_km or 0)
            } for result in results]
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close() 