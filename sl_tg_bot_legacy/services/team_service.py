from database.models.team import Team
from database.models.user import User
from database.models.running_log import RunningLog
from database.base import get_db
from sqlalchemy import func, extract, text
from utils.formatters import round_km
from datetime import datetime, timedelta
from database.logger import logger
import traceback

class TeamService:
    @staticmethod
    def create_team(team_name, created_by):
        return Team.create(team_name, created_by)

    @staticmethod
    def get_team_stats(team_id):
        """Получение статистики команды"""
        db = next(get_db())
        try:
            # Получаем статистику за последние 30 дней
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            
            stats = db.query(
                User.username,
                func.sum(RunningLog.km).label('total_km')
            ).join(
                Team.members
            ).outerjoin(
                RunningLog, User.user_id == RunningLog.user_id
            ).filter(
                Team.team_id == team_id,
                RunningLog.date_added >= thirty_days_ago
            ).group_by(
                User.username
            ).order_by(
                text('total_km DESC')
            ).all()
            
            return [{
                'username': s.username,
                'total_km': round_km(s.total_km or 0)
            } for s in stats]
        except Exception as e:
            logger.error(f"Error getting team stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    @staticmethod
    def get_user_teams_stats(user_id):
        """Получение статистики команд пользователя"""
        teams = Team.get_user_teams(user_id)
        return [{
            'team': team,
            'stats': TeamService.get_team_stats(team.team_id)
        } for team in teams] 