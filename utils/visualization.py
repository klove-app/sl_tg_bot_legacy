import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from database.db import get_connection
from utils.formatters import round_km
from datetime import datetime

def create_leaderboard_chart():
    conn = get_connection()
    cursor = conn.cursor()
    current_year = datetime.now().year

    cursor.execute("""
        SELECT u.username, COALESCE(SUM(r.km), 0) as total_km
        FROM users u
        LEFT JOIN running_log r ON u.user_id = r.user_id
        AND strftime('%Y', r.date_added) = ?
        GROUP BY u.username
        HAVING total_km > 0
        ORDER BY total_km DESC
        LIMIT 10
    """, (str(current_year),))
    
    data = cursor.fetchall()
    conn.close()

    if not data:
        return None

    # ... код создания графика ... 