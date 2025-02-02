from database.db import get_connection
from utils.formatters import round_km
from datetime import datetime
from functools import lru_cache

class StatsService:
    @staticmethod
    @lru_cache(maxsize=100)
    def get_user_stats(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        # Получаем данные пользователя
        cursor.execute("""
            SELECT u.yearly_goal,
                   COALESCE(SUM(r.km), 0) as total_km,
                   COUNT(DISTINCT r.date_added) as activity_count
            FROM users u
            LEFT JOIN running_log r ON u.user_id = r.user_id
            AND strftime('%Y', r.date_added) = ?
            WHERE u.user_id = ?
            GROUP BY u.user_id
        """, (str(datetime.now().year), user_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        yearly_goal, total_km, activity_count = result
        total_km = round_km(total_km)
        yearly_goal = round_km(yearly_goal)
        
        # Расчет процента выполнения
        completion_percentage = round_km((total_km / yearly_goal * 100) if yearly_goal > 0 else 0)
        
        return {
            'yearly_goal': yearly_goal,
            'total_km': total_km,
            'activity_count': activity_count,
            'completion_percentage': completion_percentage
        }

    @staticmethod
    def invalidate_cache(user_id):
        """Инвалидация кэша при обновлении данных"""
        StatsService.get_user_stats.cache_clear()

    @staticmethod
    def get_leaderboard():
        conn = get_connection()
        cursor = conn.cursor()
        current_year = datetime.now().year
        
        cursor.execute("""
            SELECT u.username, u.yearly_goal, COALESCE(SUM(r.km), 0) as total_km
            FROM users u
            LEFT JOIN running_log r ON u.user_id = r.user_id
            AND strftime('%Y', r.date_added) = ?
            GROUP BY u.username, u.yearly_goal
            HAVING u.yearly_goal > 0
            ORDER BY total_km DESC
        """, (str(current_year),))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'username': row[0],
                'yearly_goal': round_km(row[1]),
                'total_km': round_km(row[2])
            }
            for row in results
        ] 