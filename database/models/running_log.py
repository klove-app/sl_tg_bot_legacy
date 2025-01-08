from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, func, extract
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base, get_db, Session, SessionLocal
from database.logger import logger
from database.db import get_connection
import traceback
from typing import List

class RunningLog(Base):
    __tablename__ = "running_log"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"))
    km = Column(Float)
    date_added = Column(Date)
    notes = Column(String, nullable=True)
    chat_id = Column(String, nullable=True)

    # Отношение к пользователю
    user = relationship("User", back_populates="runs")

    @classmethod
    def add_entry(cls, user_id: str, km: float, date_added: datetime.date, notes: str = None, chat_id: str = None, db = None) -> bool:
        """Добавить новую запись о пробежке"""
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            # Проверяем максимальную дистанцию
            if km > 100:
                logger.warning(f"Attempt to add run with distance {km} km for user {user_id}")
                return False
                
            log_entry = cls(
                user_id=user_id,
                km=km,
                date_added=date_added,
                notes=notes,
                chat_id=chat_id
            )
            db.add(log_entry)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding run entry: {e}")
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()

    @classmethod
    def get_user_total_km(cls, user_id: str, db = None) -> float:
        """Получить общую дистанцию пользователя за текущий год"""
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            current_year = datetime.now().year
            result = db.query(cls).with_entities(
                func.sum(cls.km)
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == current_year
            ).scalar()
            return result or 0.0
        except Exception as e:
            logger.error(f"Error getting total km: {e}")
            return 0.0
        finally:
            if should_close:
                db.close()

    @classmethod
    def get_top_runners(cls, limit: int = 10, year: int = None) -> list:
        """Получить топ бегунов за год"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            results = db.query(
                cls.user_id,
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.avg(cls.km).label('avg_km'),
                func.max(cls.km).label('best_run')
            ).filter(
                extract('year', cls.date_added) == year
            ).group_by(
                cls.user_id
            ).order_by(
                func.sum(cls.km).desc()
            ).limit(limit).all()
            
            return [{
                'user_id': r.user_id,
                'total_km': float(r.total_km or 0),
                'runs_count': r.runs_count,
                'avg_km': float(r.avg_km or 0),
                'best_run': float(r.best_run or 0)
            } for r in results]
        except Exception as e:
            logger.error(f"Error getting top runners: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    @classmethod
    def get_user_runs(cls, user_id: str, limit: int = 5) -> List['RunningLog']:
        """Получает список последних пробежек пользователя"""
        with Session() as session:
            query = (
                session.query(cls)
                .filter(cls.user_id == user_id)
                .order_by(cls.date_added.desc())
                .limit(limit)
            )
            return query.all()

    @classmethod
    def get_user_stats(cls, user_id: str, year: int, month: int = None, db = None):
        """Получить статистику пользователя за год или месяц"""
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            query = db.query(
                func.count().label('runs_count'),
                func.sum(cls.km).label('total_km'),
                func.avg(cls.km).label('avg_km')
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == year
            )

            if month:
                query = query.filter(extract('month', cls.date_added) == month)

            result = query.first()
            
            # Проверяем, что результаты не None
            runs_count = result[0] if result[0] is not None else 0
            total_km = float(result[1]) if result[1] is not None else 0.0
            avg_km = float(result[2]) if result[2] is not None else 0.0
            
            return {
                'runs_count': runs_count,
                'total_km': total_km,
                'avg_km': avg_km
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'runs_count': 0,
                'total_km': 0.0,
                'avg_km': 0.0
            }
        finally:
            if should_close:
                db.close()

    @classmethod
    def get_best_stats(cls, user_id: str, db = None):
        """Получить лучшие показатели пользователя за текущий год"""
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            current_year = datetime.now().year
            result = db.query(
                func.max(cls.km).label('best_run'),
                func.count().label('total_runs'),
                func.sum(cls.km).label('total_km')
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == current_year
            ).first()

            if not result:
                return {
                    'best_run': 0.0,
                    'total_runs': 0,
                    'total_km': 0.0
                }

            return {
                'best_run': float(result[0] or 0),
                'total_runs': result[1] or 0,
                'total_km': float(result[2] or 0)
            }
        except Exception as e:
            logger.error(f"Error getting best stats: {e}")
            return {
                'best_run': 0.0,
                'total_runs': 0,
                'total_km': 0.0
            }
        finally:
            if should_close:
                db.close()

    @classmethod
    def get_recent_runs(cls, user_id: str, limit: int = 5):
        """Получить последние пробежки пользователя"""
        db = next(get_db())
        try:
            runs = db.query(cls).filter(
                cls.user_id == user_id
            ).order_by(
                cls.date_added.desc()
            ).limit(limit).all()

            return [{'date': run.date_added, 'distance_km': run.km} for run in runs]
        except Exception as e:
            logger.error(f"Error getting recent runs: {e}")
            return [] 

    @classmethod
    def get_chat_stats(cls, chat_id: str, year: int = None, month: int = None):
        """Получить статистику чата за год или месяц"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            # Получаем всех пользователей, которые бегали в этом году
            base_query = db.query(cls).filter(
                extract('year', cls.date_added) == year
            )
            
            if month:
                base_query = base_query.filter(extract('month', cls.date_added) == month)
            
            # Получаем статистику
            stats = base_query.with_entities(
                func.count().label('runs_count'),
                func.sum(cls.km).label('total_km'),
                func.avg(cls.km).label('avg_km'),
                func.max(cls.km).label('best_run')
            ).first()
            
            # Получаем количество уникальных пользователей
            users_count = base_query.with_entities(
                func.count(func.distinct(cls.user_id))
            ).scalar() or 0
            
            # Проверяем, что результаты не None
            runs_count = stats[0] if stats[0] is not None else 0
            total_km = float(stats[1]) if stats[1] is not None else 0.0
            avg_km = float(stats[2]) if stats[2] is not None else 0.0
            best_run = float(stats[3]) if stats[3] is not None else 0.0
            
            # Получаем статистику по месяцам, если запрошен год
            monthly_stats = []
            if not month:
                monthly_query = db.query(
                    extract('month', cls.date_added).label('month'),
                    func.sum(cls.km).label('monthly_km')
                ).filter(
                    extract('year', cls.date_added) == year
                ).group_by(
                    extract('month', cls.date_added)
                ).order_by(
                    extract('month', cls.date_added)
                ).all()
                
                monthly_stats = [{
                    'month': int(r.month),
                    'total_km': float(r.monthly_km or 0)
                } for r in monthly_query]
            
            return {
                'users_count': users_count,
                'runs_count': runs_count,
                'total_km': total_km,
                'avg_km': avg_km,
                'best_run': best_run,
                'monthly_stats': monthly_stats
            }
        except Exception as e:
            logger.error(f"Error getting chat stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'users_count': 0,
                'runs_count': 0,
                'total_km': 0.0,
                'avg_km': 0.0,
                'best_run': 0.0,
                'monthly_stats': []
            }

    @classmethod
    def get_chat_top_users(cls, chat_id: str, year: int = None, limit: int = 5):
        """Получить топ пользователей чата за год"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            results = db.query(
                cls.user_id,
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.avg(cls.km).label('avg_km'),
                func.max(cls.km).label('best_run')
            ).filter(
                cls.chat_id == chat_id,
                extract('year', cls.date_added) == year
            ).group_by(
                cls.user_id
            ).order_by(
                func.sum(cls.km).desc()
            ).limit(limit).all()
            
            return [{
                'user_id': r.user_id,
                'total_km': float(r.total_km or 0),
                'runs_count': r.runs_count,
                'avg_km': float(r.avg_km or 0),
                'best_run': float(r.best_run or 0)
            } for r in results]
        except Exception as e:
            logger.error(f"Error getting chat top users: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return [] 

    @staticmethod
    def get_chat_stats_sqlite(chat_id: str, year: int, month: int = None) -> dict:
        """Получает статистику чата за указанный год и опционально месяц"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            base_query = """
                SELECT 
                    COALESCE(SUM(km), 0) as total_km,
                    COUNT(*) as runs_count,
                    COUNT(DISTINCT user_id) as users_count
                FROM running_log
                WHERE chat_id = ? 
                AND strftime('%Y', date_added) = ?
            """
            
            params = [chat_id, str(year)]
            
            if month is not None:
                base_query += " AND strftime('%m', date_added) = ?"
                # Добавляем ведущий ноль для месяцев 1-9
                params.append(str(month).zfill(2))
            
            print(f"""
            Debug info:
            - Total KM: {cursor.execute("SELECT SUM(km) FROM running_log WHERE chat_id = ? AND strftime('%Y', date_added) = ?", [chat_id, str(year)]).fetchone()[0]}
            - Number of runs: {cursor.execute("SELECT COUNT(*) FROM running_log WHERE chat_id = ? AND strftime('%Y', date_added) = ?", [chat_id, str(year)]).fetchone()[0]}
            - Number of unique users: {cursor.execute("SELECT COUNT(DISTINCT user_id) FROM running_log WHERE chat_id = ? AND strftime('%Y', date_added) = ?", [chat_id, str(year)]).fetchone()[0]}
            - Chat ID used in query: {chat_id}
            - Year used in query: {year}
            """)
            
            cursor.execute(base_query, params)
            result = cursor.fetchone()
            
            return {
                'total_km': result[0] or 0,
                'runs_count': result[1] or 0,
                'users_count': result[2] or 0
            }
            
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_top_runners_sqlite(chat_id: str, year: int, limit: int = 3) -> list:
        """Получает топ бегунов чата за указанный год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    r.user_id,
                    SUM(r.km) as total_km,
                    COUNT(*) as runs_count
                FROM running_log r
                WHERE r.chat_id = ? 
                AND strftime('%Y', r.date_added) = ?
                GROUP BY r.user_id
                ORDER BY total_km DESC
                LIMIT ?
            """
            
            cursor.execute(query, (chat_id, str(year), limit))
            results = cursor.fetchall()
            
            # Получаем имена пользователей отдельным запросом
            formatted_results = []
            for row in results:
                user_id = row[0]
                cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
                user_result = cursor.fetchone()
                username = user_result[0] if user_result else f"User {user_id}"
                
                formatted_results.append({
                    'user_name': username,
                    'total_km': row[1],
                    'runs_count': row[2]
                })
            
            return formatted_results
            
        finally:
            cursor.close()
            conn.close() 

    @staticmethod
    def get_chat_stats_until_date_sqlite(chat_id: str, year: int, month: int, day: int) -> dict:
        """Получает статистику чата за указанный год до определенной даты"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    COALESCE(SUM(km), 0) as total_km,
                    COUNT(*) as runs_count,
                    COUNT(DISTINCT user_id) as users_count
                FROM running_log
                WHERE chat_id = ? 
                AND strftime('%Y', date_added) = ?
                AND (
                    strftime('%m', date_added) < ? 
                    OR (
                        strftime('%m', date_added) = ? 
                        AND strftime('%d', date_added) <= ?
                    )
                )
            """
            
            # Добавляем ведущие нули для месяца и дня
            month_str = str(month).zfill(2)
            day_str = str(day).zfill(2)
            
            cursor.execute(query, (chat_id, str(year), month_str, month_str, day_str))
            result = cursor.fetchone()
            
            return {
                'total_km': result[0] or 0,
                'runs_count': result[1] or 0,
                'users_count': result[2] or 0
            }
            
        finally:
            cursor.close()
            conn.close() 