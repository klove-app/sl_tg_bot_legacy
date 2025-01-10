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
    chat_type = Column(String, nullable=True)

    # Отношение к пользователю
    user = relationship("User", back_populates="runs")

    @classmethod
    def add_entry(cls, user_id: str, km: float, date_added: datetime.date, notes: str = None, chat_id: str = None, chat_type: str = None, db = None) -> bool:
        """Добавить новую запись о пробежке"""
        logger.info(f"Adding new run entry for user {user_id}: {km} km, chat_id: {chat_id}, chat_type: {chat_type}")
        
        if db is None:
            logger.debug("Creating new database session")
            db = SessionLocal()
            should_close = True
        else:
            logger.debug("Using existing database session")
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
                chat_id=chat_id,
                chat_type=chat_type
            )
            logger.debug(f"Created log entry: {log_entry.__dict__}")
            
            db.add(log_entry)
            logger.debug("Added log entry to session")
            
            db.commit()
            logger.info(f"Successfully committed run entry for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding run entry: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return False
        finally:
            if should_close:
                logger.debug("Closing database session")
                db.close()

    @classmethod
    def get_user_total_km(cls, user_id: str, chat_type: str = None, db = None) -> float:
        """Получить общую дистанцию пользователя за текущий год"""
        logger.info(f"Getting total km for user {user_id}, chat_type: {chat_type}")
        
        if db is None:
            logger.debug("Creating new database session")
            db = SessionLocal()
            should_close = True
        else:
            logger.debug("Using existing database session")
            should_close = False
            
        try:
            current_year = datetime.now().year
            query = db.query(cls).with_entities(
                func.sum(cls.km)
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == current_year
            )
            
            if chat_type:
                query = query.filter(cls.chat_type == chat_type)
            
            logger.debug(f"Executing query: {query}")
            result = query.scalar()
            logger.info(f"Total km for user {user_id}: {result or 0.0}")
            return result or 0.0
        except Exception as e:
            logger.error(f"Error getting total km: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 0.0
        finally:
            if should_close:
                logger.debug("Closing database session")
                db.close()

    @classmethod
    def get_top_runners(cls, limit: int = 10, year: int = None) -> list:
        """Получить топ бегунов за год (включая всех пользователей)"""
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
    def get_user_global_rank(cls, user_id: str, year: int = None) -> dict:
        """Получить позицию пользователя в глобальном рейтинге"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            # Подзапрос для получения общего километража каждого пользователя
            subq = db.query(
                cls.user_id,
                func.sum(cls.km).label('total_km')
            ).filter(
                extract('year', cls.date_added) == year
            ).group_by(
                cls.user_id
            ).subquery()
            
            # Получаем ранг пользователя
            rank_query = db.query(
                func.row_number().over(
                    order_by=subq.c.total_km.desc()
                ).label('rank'),
                subq.c.user_id,
                subq.c.total_km
            ).from_self().filter(
                subq.c.user_id == user_id
            ).first()
            
            if rank_query:
                total_users = db.query(
                    func.count(func.distinct(cls.user_id))
                ).filter(
                    extract('year', cls.date_added) == year
                ).scalar()
                
                return {
                    'rank': rank_query.rank,
                    'total_users': total_users,
                    'total_km': float(rank_query.total_km or 0)
                }
            return {'rank': 0, 'total_users': 0, 'total_km': 0.0}
            
        except Exception as e:
            logger.error(f"Error getting user global rank: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'rank': 0, 'total_users': 0, 'total_km': 0.0}

    @classmethod
    def get_personal_stats(cls, user_id: str, year: int = None) -> dict:
        """Получить подробную личную статистику пользователя"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            # Базовая статистика
            base_stats = cls.get_user_stats(user_id, year)
            
            # Дополнительная статистика
            additional_stats = db.query(
                func.max(cls.km).label('longest_run'),
                func.min(cls.km).label('shortest_run'),
                func.avg(cls.km).label('average_run'),
                func.count(func.distinct(cls.date_added)).label('active_days')
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == year
            ).first()
            
            # Статистика по месяцам
            monthly_stats = db.query(
                extract('month', cls.date_added).label('month'),
                func.sum(cls.km).label('monthly_km')
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == year
            ).group_by(
                extract('month', cls.date_added)
            ).all()
            
            return {
                **base_stats,
                'longest_run': float(additional_stats.longest_run or 0),
                'shortest_run': float(additional_stats.shortest_run or 0),
                'average_run': float(additional_stats.average_run or 0),
                'active_days': additional_stats.active_days or 0,
                'monthly_progress': [
                    {'month': int(stat.month), 'km': float(stat.monthly_km or 0)}
                    for stat in monthly_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting personal stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'runs_count': 0,
                'total_km': 0.0,
                'avg_km': 0.0,
                'longest_run': 0.0,
                'shortest_run': 0.0,
                'average_run': 0.0,
                'active_days': 0,
                'monthly_progress': []
            }

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
        logger.info(f"Getting stats for user {user_id}, year: {year}, month: {month}")
        
        if db is None:
            logger.debug("Creating new database session")
            db = SessionLocal()
            should_close = True
        else:
            logger.debug("Using existing database session")
            should_close = False
            
        try:
            # Базовый запрос
            query = db.query(
                func.count().label('runs_count'),
                func.sum(cls.km).label('total_km'),
                func.avg(cls.km).label('avg_km')
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == year
            )
            
            # Добавляем фильтр по месяцу, если указан
            if month:
                query = query.filter(extract('month', cls.date_added) == month)
            
            logger.debug(f"Executing query: {query}")
            result = query.first()
            
            # Формируем статистику по типам чатов
            chat_stats_query = db.query(
                cls.chat_type,
                func.count().label('runs_count'),
                func.sum(cls.km).label('total_km'),
                func.avg(cls.km).label('avg_km')
            ).filter(
                cls.user_id == user_id,
                extract('year', cls.date_added) == year,
                cls.chat_type.isnot(None)
            )
            
            if month:
                chat_stats_query = chat_stats_query.filter(extract('month', cls.date_added) == month)
            
            chat_stats_query = chat_stats_query.group_by(cls.chat_type)
            logger.debug(f"Executing chat stats query: {chat_stats_query}")
            chat_stats = chat_stats_query.all()
            
            stats = {
                'runs_count': result.runs_count or 0,
                'total_km': float(result.total_km or 0),
                'avg_km': float(result.avg_km or 0),
                'chat_stats': {
                    stat.chat_type: {
                        'runs_count': stat.runs_count,
                        'total_km': float(stat.total_km or 0),
                        'avg_km': float(stat.avg_km or 0)
                    } for stat in chat_stats
                }
            }
            
            logger.info(f"Stats for user {user_id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                'runs_count': 0,
                'total_km': 0.0,
                'avg_km': 0.0,
                'chat_stats': {}
            }
        finally:
            if should_close:
                logger.debug("Closing database session")
                db.close()

    @classmethod
    def get_best_stats(cls, user_id: str, chat_type: str = None, db = None):
        """Получить лучшие показатели пользователя"""
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            query = db.query(
                func.max(cls.km).label('best_run'),
                func.count().label('total_runs'),
                func.sum(cls.km).label('total_km')
            ).filter(
                cls.user_id == user_id
            )
            
            if chat_type:
                query = query.filter(cls.chat_type == chat_type)
                
            result = query.first()
            
            return {
                'best_run': float(result.best_run or 0),
                'total_runs': result.total_runs or 0,
                'total_km': float(result.total_km or 0)
            }
        except Exception as e:
            logger.error(f"Error getting best stats: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'best_run': 0.0, 'total_runs': 0, 'total_km': 0.0}
        finally:
            if should_close:
                db.close()

    @classmethod
    def get_recent_runs(cls, user_id: str, chat_type: str = None, limit: int = 5):
        """Получить последние пробежки пользователя"""
        db = next(get_db())
        try:
            query = db.query(cls).filter(
                cls.user_id == user_id
            )
            
            if chat_type:
                query = query.filter(cls.chat_type == chat_type)
                
            runs = query.order_by(
                cls.date_added.desc()
            ).limit(limit).all()

            return [{'date': run.date_added, 'distance_km': run.km} for run in runs]
        except Exception as e:
            logger.error(f"Error getting recent runs: {e}")
            return []

    @classmethod
    def get_chat_stats(cls, chat_id: str, year: int = None, month: int = None, chat_type: str = None):
        """Получить статистику чата за год или месяц"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            # Получаем всех пользователей, которые бегали в этом году
            base_query = db.query(cls).filter(
                extract('year', cls.date_added) == year
            )
            
            if chat_id:
                base_query = base_query.filter(cls.chat_id == chat_id)
            
            if chat_type:
                base_query = base_query.filter(cls.chat_type == chat_type)
            
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
                )
                
                if chat_id:
                    monthly_query = monthly_query.filter(cls.chat_id == chat_id)
                    
                if chat_type:
                    monthly_query = monthly_query.filter(cls.chat_type == chat_type)
                
                monthly_query = monthly_query.group_by(
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
    def get_chat_top_users(cls, chat_id: str, year: int = None, limit: int = 5, chat_type: str = None):
        """Получить топ пользователей чата за год"""
        if year is None:
            year = datetime.now().year
            
        db = next(get_db())
        try:
            query = db.query(
                cls.user_id,
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.avg(cls.km).label('avg_km'),
                func.max(cls.km).label('best_run')
            ).filter(
                extract('year', cls.date_added) == year
            )
            
            if chat_id:
                query = query.filter(cls.chat_id == chat_id)
                
            if chat_type:
                query = query.filter(cls.chat_type == chat_type)
            
            results = query.group_by(
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
    def get_chat_stats_sqlite(chat_id: str, year: int, month: int = None, chat_type: str = None) -> dict:
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
            
            if chat_type:
                base_query += " AND chat_type = ?"
                params.append(chat_type)
            
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
    def get_top_runners_sqlite(chat_id: str, year: int, limit: int = 3, chat_type: str = None) -> list:
        """Получает топ бегунов чата за указанный год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            base_query = """
                SELECT 
                    r.user_id,
                    SUM(r.km) as total_km,
                    COUNT(*) as runs_count
                FROM running_log r
                WHERE r.chat_id = ? 
                AND strftime('%Y', r.date_added) = ?
            """
            
            params = [chat_id, str(year)]
            
            if chat_type:
                base_query += " AND r.chat_type = ?"
                params.append(chat_type)
            
            base_query += """
                GROUP BY r.user_id
                ORDER BY total_km DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(base_query, params)
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
    def get_chat_stats_until_date_sqlite(chat_id: str, year: int, month: int, day: int, chat_type: str = None) -> dict:
        """Получает статистику чата за указанный год до определенной даты"""
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
            
            params = [chat_id, str(year), month_str, month_str, day_str]
            
            if chat_type:
                base_query += " AND chat_type = ?"
                params.append(chat_type)
            
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
    def get_total_stats(year: int, month: int = None, chat_type: str = None) -> dict:
        """Получает общую статистику за год или месяц"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            base_query = """
                SELECT 
                    COALESCE(SUM(km), 0) as total_km,
                    COUNT(*) as runs_count,
                    COUNT(DISTINCT user_id) as users_count,
                    COALESCE(AVG(km), 0) as avg_km
                FROM running_log
                WHERE strftime('%Y', date_added) = ?
            """
            params = [str(year)]
            
            if month:
                base_query += " AND strftime('%m', date_added) = ?"
                params.append(str(month).zfill(2))
                
            if chat_type:
                base_query += " AND chat_type = ?"
                params.append(chat_type)
            
            cursor.execute(base_query, params)
            result = cursor.fetchone()
            
            return {
                'total_km': result[0] or 0,
                'runs_count': result[1] or 0,
                'users_count': result[2] or 0,
                'avg_km': result[3] or 0
            }
            
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_chat_stats_all(year: int) -> list:
        """Получает статистику по всем чатам за год"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT 
                    chat_id,
                    COALESCE(SUM(km), 0) as total_km,
                    COUNT(*) as runs_count,
                    COUNT(DISTINCT user_id) as users_count
                FROM running_log
                WHERE strftime('%Y', date_added) = ?
                AND chat_id IS NOT NULL
                GROUP BY chat_id
            """
            
            cursor.execute(query, (str(year),))
            results = cursor.fetchall()
            
            return [
                {
                    'chat_id': row[0],
                    'total_km': row[1] or 0,
                    'runs_count': row[2] or 0,
                    'users_count': row[3] or 0
                }
                for row in results
            ]
            
        finally:
            cursor.close()
            conn.close() 