from database.models.challenge import Challenge
from database.db import get_connection
from utils.formatters import round_km
from datetime import datetime, date

class ChallengeService:
    @staticmethod
    def get_active_challenges():
        """Получение списка активных челленджей"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.*, COUNT(cp.user_id) as participants
            FROM challenges c
            LEFT JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
            WHERE c.end_date >= date('now')
            GROUP BY c.challenge_id
            ORDER BY c.start_date
        """)
        
        challenges = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'title': row[1],
                'goal_km': round_km(row[2]),
                'start_date': row[3],
                'end_date': row[4],
                'description': row[5],
                'created_by': row[6],
                'participants_count': row[7]
            }
            for row in challenges
        ]

    @staticmethod
    def create_challenge(title, goal_km, start_date, end_date, description, created_by):
        return Challenge.create(title, goal_km, start_date, end_date, description, created_by)

    @staticmethod
    def get_challenge_stats(challenge_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username,
                   COALESCE(SUM(r.km), 0) as total_km,
                   COUNT(DISTINCT r.date_added) as active_days
            FROM challenge_participants cp
            JOIN users u ON cp.user_id = u.user_id
            LEFT JOIN running_log r ON u.user_id = r.user_id
            JOIN challenges c ON cp.challenge_id = c.challenge_id
            WHERE cp.challenge_id = ?
            AND r.date_added BETWEEN c.start_date AND c.end_date
            GROUP BY u.username
            ORDER BY total_km DESC
        """, (challenge_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'username': row[0],
                'total_km': round_km(row[1]),
                'active_days': row[2]
            }
            for row in results
        ]

    @staticmethod
    def get_user_challenges(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.*, COALESCE(SUM(r.km), 0) as total_km
            FROM challenges c
            JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
            LEFT JOIN running_log r ON cp.user_id = r.user_id
            AND r.date_added BETWEEN c.start_date AND c.end_date
            WHERE cp.user_id = ?
            GROUP BY c.challenge_id
            ORDER BY c.end_date DESC
        """, (user_id,))
        
        challenges = cursor.fetchall()
        conn.close()
        
        return [
            {
                'challenge': Challenge(c[0], c[1], c[2], c[3], c[4], c[5], c[6]),
                'total_km': round_km(c[7])
            }
            for c in challenges
        ]

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
            
            challenge_id = Challenge.create(
                title=title,
                goal_km=0,  # Начальная цель
                start_date=start_date,
                end_date=end_date,
                chat_id=chat_id,
                is_system=True
            )
            
            challenge = Challenge.get_by_id(challenge_id)
            
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