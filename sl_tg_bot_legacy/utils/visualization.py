import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
from database.base import get_db
from database.models.user import User
from database.models.running_log import RunningLog
from sqlalchemy import func, extract
from utils.formatters import round_km
from datetime import datetime, timedelta
from database.logger import logger
import traceback

def create_leaderboard_chart():
    """Создание графика лидеров"""
    db = next(get_db())
    try:
        current_year = datetime.now().year

        results = db.query(
            User.username,
            func.sum(RunningLog.km).label('total_km')
        ).outerjoin(
            RunningLog,
            (User.user_id == RunningLog.user_id) &
            (extract('year', RunningLog.date_added) == current_year)
        ).group_by(
            User.username
        ).having(
            func.sum(RunningLog.km) > 0
        ).order_by(
            func.sum(RunningLog.km).desc()
        ).limit(10).all()

        if not results:
            return None

        # Создаем график
        plt.figure(figsize=(10, 6))
        plt.barh([r.username for r in results], [round_km(r.total_km or 0) for r in results])
        plt.xlabel('Километры')
        plt.ylabel('Пользователи')
        plt.title(f'Топ-10 бегунов {current_year} года')

        # Сохраняем график в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Error creating leaderboard chart: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None
    finally:
        db.close() 