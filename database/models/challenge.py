from database.db import get_connection
from datetime import datetime
from utils.formatters import round_km
import traceback
import logging

logger = logging.getLogger(__name__)

class Challenge:
    def __init__(self, challenge_id=None, title=None, goal_km=None, start_date=None, end_date=None, chat_id=None, is_system=False, user_id=None):
        self.challenge_id = challenge_id
        self.title = title
        self.goal_km = goal_km
        self.start_date = start_date
        self.end_date = end_date
        self.chat_id = chat_id
        self.is_system = is_system
        self.user_id = user_id

    @staticmethod
    def create_personal_challenge(title, goal_km, start_date, end_date, description, created_by):
        """Создает персональный челлендж"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO challenges (title, goal_km, start_date, end_date, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, round_km(goal_km), start_date, end_date, description, created_by))
        
        challenge_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return Challenge(challenge_id, title, description, start_date, end_date, goal_km, created_by)

    def add_participant(self, user_id):
        """Добавляет участника в системный челлендж"""
        # Для системного челленджа не нужно явно добавлять участников,
        # так как учитываются все пользователи чата автоматически
        pass

    @staticmethod
    def get_active_challenges():
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM challenges
            WHERE end_date >= date('now')
            ORDER BY start_date
        """)
        
        challenges = cursor.fetchall()
        conn.close()
        
        return [Challenge(c[0], c[1], c[2], c[3], c[4], c[5], c[6]) for c in challenges] 

    @staticmethod
    def get_system_challenge(chat_id, year):
        """Получает системный челлендж для чата на указанный год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Нормализуем chat_id
            normalized_chat_id = chat_id.replace('-100', '')
            
            print(f"Looking for challenge: chat_id={normalized_chat_id}, year={year}")
            
            cursor.execute("""
                SELECT challenge_id, title, goal_km, start_date, end_date, chat_id, is_system
                FROM challenges 
                WHERE chat_id = ? 
                AND strftime('%Y', start_date) = ? 
                AND is_system = 1
            """, (normalized_chat_id, str(year)))
            
            row = cursor.fetchone()
            if row:
                print(f"Found challenge: {row}")
                return Challenge(
                    challenge_id=row[0],
                    title=row[1],
                    goal_km=row[2],
                    start_date=row[3],
                    end_date=row[4],
                    chat_id=row[5],
                    is_system=bool(row[6])
                )
            return None
            
        finally:
            conn.close()

    @staticmethod
    def create(title, goal_km, start_date, end_date, chat_id, is_system=False):
        """Создает новый челлендж"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO challenges (title, goal_km, start_date, end_date, chat_id, is_system)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, goal_km, start_date, end_date, chat_id, 1 if is_system else 0))
            
            conn.commit()
            return cursor.lastrowid
            
        finally:
            conn.close()

    def update_goal(self, new_goal_km):
        """Обновляет цель челленджа"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE challenges
                SET goal_km = ?
                WHERE challenge_id = ?
                """, (new_goal_km, self.challenge_id))
            
            conn.commit()
            self.goal_km = new_goal_km
            
        finally:
            conn.close()

    @staticmethod
    def get_by_id(challenge_id):
        """Получает челлендж по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT challenge_id, title, goal_km, start_date, end_date, chat_id, is_system
                FROM challenges
                WHERE challenge_id = ?
                """, (challenge_id,))
            
            row = cursor.fetchone()
            if row:
                return Challenge(
                    challenge_id=row[0],
                    title=row[1],
                    goal_km=row[2],
                    start_date=row[3],
                    end_date=row[4],
                    chat_id=row[5],
                    is_system=bool(row[6])
                )
            return None
            
        finally:
            conn.close()

    def get_participants_count(self):
        """Получает количество активных участников в чате"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Нормализуем chat_id (убираем префикс -100 если он есть)
            normalized_chat_id = self.chat_id.replace('-100', '')
            
            print(f"Debug: Getting active participants for chat_id={normalized_chat_id}")
            
            # Получаем только тех пользователей, которые сейчас в чате
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id)
                FROM users
                WHERE user_id IN (
                    SELECT DISTINCT user_id 
                    FROM running_log 
                    WHERE chat_id = ?
                )
                AND is_active = 1  -- добавим эту колонку для отслеживания активных пользователей
            """, (normalized_chat_id,))
            
            count = cursor.fetchone()[0]
            print(f"Found {count} active participants")
            
            return count
            
        except Exception as e:
            print(f"Error in get_participants_count: {e}")
            return 0
        finally:
            conn.close()

    def get_total_progress(self):
        """Получает общий прогресс всех участников чата за год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Используем год из start_date
            year = datetime.strptime(self.start_date, '%Y-%m-%d').year if isinstance(self.start_date, str) else self.start_date.year
            
            # Нормализуем chat_id (убираем префикс -100 если он есть)
            normalized_chat_id = self.chat_id.replace('-100', '')
            
            print(f"Debug: original chat_id={self.chat_id}, normalized={normalized_chat_id}, year={year}")
            
            query = """
                SELECT COALESCE(SUM(km), 0) as total_km,
                       COUNT(*) as runs_count,
                       COUNT(DISTINCT user_id) as users_count
                FROM running_log 
                WHERE chat_id = ? 
                AND strftime('%Y', date_added) = ?
            """
            
            cursor.execute(query, (normalized_chat_id, str(year)))
            result = cursor.fetchone()
            total_km, runs_count, users_count = result
            
            print(f"""
            Debug info:
            - Total KM: {total_km}
            - Number of runs: {runs_count}
            - Number of unique users: {users_count}
            - Chat ID used in query: {normalized_chat_id}
            - Year used in query: {year}
            """)
            
            return round(total_km, 2) if total_km else 0.0
            
        except Exception as e:
            print(f"Error in get_total_progress: {e}")
            import traceback
            traceback.print_exc()
            return 0.0
        finally:
            conn.close()

    @staticmethod
    def get_chat_participants(chat_id):
        """Получает список всех участников чата, которые когда-либо регистрировали пробежки"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DISTINCT u.user_id, u.username
                FROM users u
                JOIN running_log r ON u.user_id = r.user_id
                WHERE r.chat_id = ?
            """, (chat_id,))
            
            return cursor.fetchall()
            
        finally:
            conn.close() 

    def save(self):
        """Сохраняет или обновляет челлендж в базе данных"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if self.challenge_id:
                # Обновляем существующий челлендж
                cursor.execute("""
                    UPDATE challenges
                    SET title = ?, goal_km = ?, start_date = ?, end_date = ?, chat_id = ?, is_system = ?
                    WHERE challenge_id = ?
                """, (
                    self.title,
                    self.goal_km,
                    self.start_date,
                    self.end_date,
                    self.chat_id,
                    1 if self.is_system else 0,
                    self.challenge_id
                ))
            else:
                # Создаем новый челлендж
                cursor.execute("""
                    INSERT INTO challenges (title, goal_km, start_date, end_date, chat_id, is_system)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.title,
                    self.goal_km,
                    self.start_date,
                    self.end_date,
                    self.chat_id,
                    1 if self.is_system else 0
                ))
                self.challenge_id = cursor.lastrowid
            
            conn.commit()
            
        finally:
            conn.close()

    @staticmethod
    def get_user_challenge(user_id, year):
        """Получает активный челлендж пользователя на указанный год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            print(f"\n>>> Getting challenge for user {user_id} and year {year}")
            
            cursor.execute("""
                SELECT c.challenge_id, c.title, c.goal_km, c.start_date, c.end_date, c.chat_id, c.is_system
                FROM challenges c
                JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
                WHERE cp.user_id = ? 
                AND strftime('%Y', c.start_date) = ?
                AND c.is_system = 1
                ORDER BY c.start_date DESC
                LIMIT 1
            """, (user_id, str(year)))
            
            row = cursor.fetchone()
            print(f">>> Database returned: {row}")
            
            if row:
                challenge = Challenge(
                    challenge_id=row[0],
                    title=row[1],
                    goal_km=row[2],
                    start_date=row[3],
                    end_date=row[4],
                    chat_id=row[5],
                    is_system=bool(row[6])
                )
                print(f">>> Created challenge object: {challenge.__dict__}")
                return challenge
                
            print(">>> No challenge found, returning default")
            return Challenge(goal_km=0)
            
        finally:
            conn.close() 

    @staticmethod
    def get_chat_challenge(chat_id: str, year: int) -> 'Challenge':
        """Получает цель чата на указанный год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Нормализуем chat_id (убираем префикс -100 если он есть)
            normalized_chat_id = chat_id.replace('-100', '')
            
            cursor.execute("""
                SELECT challenge_id, title, goal_km, start_date, end_date, chat_id, is_system
                FROM challenges 
                WHERE chat_id = ? 
                AND strftime('%Y', start_date) = ?
                AND is_system = 0
            """, (normalized_chat_id, str(year)))
            
            row = cursor.fetchone()
            if row:
                return Challenge(
                    challenge_id=row[0],
                    title=row[1],
                    goal_km=row[2],
                    start_date=row[3],
                    end_date=row[4],
                    chat_id=row[5],
                    is_system=bool(row[6])
                )
            return None
            
        finally:
            conn.close()

    @staticmethod
    def get_all_user_challenges(user_id):
        """Получает все активные цели пользователя"""
        with get_connection() as conn:
            cursor = conn.cursor()
            print(f">>> Getting all challenges for user {user_id}")
            
            # Добавляем отладочный запрос
            cursor.execute("SELECT * FROM challenge_participants WHERE user_id = ?", (user_id,))
            participants = cursor.fetchall()
            print(f">>> Found participants: {participants}")
            
            cursor.execute("SELECT * FROM challenges WHERE is_system = 1", ())
            challenges = cursor.fetchall()
            print(f">>> All system challenges: {challenges}")
            
            # Основной запрос
            cursor.execute("""
                SELECT c.challenge_id, c.title, c.goal_km, c.start_date, c.end_date, 
                       c.chat_id, c.is_system
                FROM challenges c
                JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
                WHERE cp.user_id = ? 
                AND c.is_system = 1
                ORDER BY c.start_date DESC
            """, (user_id,))
            
            challenges = []
            for row in cursor.fetchall():
                challenge = Challenge(
                    challenge_id=row[0],
                    title=row[1],
                    goal_km=row[2],
                    start_date=row[3],
                    end_date=row[4],
                    chat_id=row[5],
                    is_system=bool(row[6])
                )
                challenges.append(challenge)
            
            print(f">>> Found {len(challenges)} challenges")
            return challenges 

    @staticmethod
    def clear_user_challenges(user_id):
        """Очищает все личные цели пользователя"""
        with get_connection() as conn:
            cursor = conn.cursor()
            print(f">>> Clearing challenges for user {user_id}")
            
            try:
                # Сначала получаем ID всех личных целей пользователя
                cursor.execute("""
                    SELECT c.challenge_id
                    FROM challenges c
                    JOIN challenge_participants cp ON c.challenge_id = cp.challenge_id
                    WHERE cp.user_id = ? 
                    AND c.is_system = 1
                """, (user_id,))
                
                challenge_ids = [row[0] for row in cursor.fetchall()]
                print(f">>> Found {len(challenge_ids)} challenges to delete")
                
                if challenge_ids:
                    # Сначала удаляем записи из challenge_participants
                    placeholders = ','.join(['?' for _ in challenge_ids])
                    cursor.execute(f"""
                        DELETE FROM challenge_participants
                        WHERE challenge_id IN ({placeholders})
                    """, challenge_ids)
                    
                    # Затем удаляем сами челленджи
                    cursor.execute(f"""
                        DELETE FROM challenges
                        WHERE challenge_id IN ({placeholders})
                    """, challenge_ids)
                    
                    conn.commit()
                    print(f">>> Successfully deleted {len(challenge_ids)} challenges")
                    return True
                    
                return False
                
            except Exception as e:
                print(f">>> Error clearing challenges: {str(e)}")
                conn.rollback()
                raise 

    def get_year_progress(self):
        """Получает прогресс с начала года"""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            if self.is_system:  # Для личной цели
                print(f">>> Getting year progress for personal challenge {self.challenge_id}")
                
                # Получаем user_id из challenge_participants
                cursor.execute("""
                    SELECT user_id 
                    FROM challenge_participants 
                    WHERE challenge_id = ?
                """, (self.challenge_id,))
                user_id = cursor.fetchone()
                
                if not user_id:
                    print(">>> No user_id found")
                    return 0.0
                    
                # Используем правильное название колонки date_added
                cursor.execute("""
                    SELECT COALESCE(SUM(km), 0)
                    FROM running_log
                    WHERE user_id = ?
                    AND strftime('%Y', date_added) = ?
                """, (user_id[0], self.start_date[:4]))
                
                result = cursor.fetchone()
                total_km = float(result[0]) if result else 0.0
                print(f">>> Year progress: {total_km} km")
                return total_km 