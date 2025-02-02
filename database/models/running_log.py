from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, func, extract, text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base, get_db, Session, SessionLocal
from database.logger import logger
import traceback
from typing import List

class RunningLog(Base):
    __tablename__ = "running_log"

    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), index=True)
    km = Column(Float)
    date_added = Column(Date, index=True)
    notes = Column(String, nullable=True)
    chat_id = Column(String, nullable=True, index=True)
    chat_type = Column(String, nullable=True, index=True)

    # Отношение к пользователю
    user = relationship("User", back_populates="runs")

    # Создаем составные индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'date_added'),
        Index('idx_chat_date', 'chat_id', 'date_added'),
    )

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
            
            stats = {
                'runs_count': result.runs_count or 0,
                'total_km': float(result.total_km or 0),
                'avg_km': float(result.avg_km or 0)
            }
            
            logger.info(f"Stats for user {user_id}: {stats}")
            return stats
            
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
        """Получить статистику чата"""
        if year is None:
            year = datetime.now().year

        db = next(get_db())
        try:
            query = db.query(
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.count(func.distinct(cls.user_id)).label('users_count')
            ).filter(
                cls.chat_id == chat_id,
                extract('year', cls.date_added) == year
            )

            if month is not None:
                query = query.filter(extract('month', cls.date_added) == month)

            if chat_type is not None:
                query = query.filter(cls.chat_type == chat_type)

            result = query.first()
            
            return {
                'total_km': float(result.total_km or 0),
                'runs_count': result.runs_count or 0,
                'users_count': result.users_count or 0
            }
        except Exception as e:
            logger.error(f"Error getting chat stats: {e}")
            return {'total_km': 0, 'runs_count': 0, 'users_count': 0}

    @classmethod
    def get_chat_top_users(cls, chat_id: str, year: int = None, limit: int = 5, chat_type: str = None):
        """Получить топ пользователей чата"""
        if year is None:
            year = datetime.now().year

        db = next(get_db())
        try:
            query = db.query(
                cls.user_id,
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count')
            ).filter(
                cls.chat_id == chat_id,
                extract('year', cls.date_added) == year
            )

            if chat_type is not None:
                query = query.filter(cls.chat_type == chat_type)

            results = query.group_by(
                cls.user_id
            ).order_by(
                text('total_km DESC')
            ).limit(limit).all()

            return [{
                'user_id': result.user_id,
                'total_km': float(result.total_km or 0),
                'runs_count': result.runs_count
            } for result in results]
        except Exception as e:
            logger.error(f"Error getting chat top users: {e}")
            return []

    @classmethod
    def get_chat_stats_until_date(cls, chat_id: str, year: int, month: int, day: int, chat_type: str = None):
        """Получить статистику чата до определенной даты"""
        db = next(get_db())
        try:
            query = db.query(
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.count(func.distinct(cls.user_id)).label('users_count')
            ).filter(
                cls.chat_id == chat_id,
                extract('year', cls.date_added) == year,
                extract('month', cls.date_added) == month,
                extract('day', cls.date_added) <= day
            )

            if chat_type is not None:
                query = query.filter(cls.chat_type == chat_type)

            result = query.first()
            
            return {
                'total_km': float(result.total_km or 0),
                'runs_count': result.runs_count or 0,
                'users_count': result.users_count or 0
            }
        except Exception as e:
            logger.error(f"Error getting chat stats until date: {e}")
            return {'total_km': 0, 'runs_count': 0, 'users_count': 0}

    @classmethod
    def get_total_stats(cls, year: int, month: int = None, chat_type: str = None):
        """Получить общую статистику по всем чатам"""
        db = next(get_db())
        try:
            query = db.query(
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.count(func.distinct(cls.user_id)).label('users_count'),
                func.count(func.distinct(cls.chat_id)).label('chats_count')
            ).filter(
                extract('year', cls.date_added) == year
            )

            if month is not None:
                query = query.filter(extract('month', cls.date_added) == month)

            if chat_type is not None:
                query = query.filter(cls.chat_type == chat_type)

            result = query.first()
            
            return {
                'total_km': float(result.total_km or 0),
                'runs_count': result.runs_count or 0,
                'users_count': result.users_count or 0,
                'chats_count': result.chats_count or 0
            }
        except Exception as e:
            logger.error(f"Error getting total stats: {e}")
            return {'total_km': 0, 'runs_count': 0, 'users_count': 0, 'chats_count': 0}

    @classmethod
    def get_chat_stats_all(cls, year: int):
        """Получить статистику по всем чатам"""
        db = next(get_db())
        try:
            results = db.query(
                cls.chat_id,
                func.sum(cls.km).label('total_km'),
                func.count().label('runs_count'),
                func.count(func.distinct(cls.user_id)).label('users_count')
            ).filter(
                extract('year', cls.date_added) == year
            ).group_by(
                cls.chat_id
            ).order_by(
                text('total_km DESC')
            ).all()

            return [{
                'chat_id': result.chat_id,
                'total_km': float(result.total_km or 0),
                'runs_count': result.runs_count,
                'users_count': result.users_count
            } for result in results]
        except Exception as e:
            logger.error(f"Error getting all chat stats: {e}")
            return [] 