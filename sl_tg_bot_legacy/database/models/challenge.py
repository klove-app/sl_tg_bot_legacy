from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, func, extract, text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base, get_db, Session, SessionLocal
from database.logger import logger
from utils.formatters import round_km
import traceback

class Challenge(Base):
    __tablename__ = "challenges"

    challenge_id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    goal_km = Column(Float)
    start_date = Column(Date)
    end_date = Column(Date)
    chat_id = Column(String, nullable=True)
    is_system = Column(Boolean, default=False)
    user_id = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_by = Column(String, nullable=True)

    @classmethod
    def create_personal_challenge(cls, title, goal_km, start_date, end_date, description, created_by):
        """Создает персональный челлендж"""
        db = next(get_db())
        try:
            challenge = cls(
                title=title,
                goal_km=round_km(goal_km),
                start_date=start_date,
                end_date=end_date,
                description=description,
                created_by=created_by
            )
            db.add(challenge)
            db.commit()
            db.refresh(challenge)
            return challenge
        except Exception as e:
            logger.error(f"Error creating personal challenge: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return None
        finally:
            db.close()

    def add_participant(self, user_id):
        """Добавляет участника в системный челлендж"""
        # Для системного челленджа не нужно явно добавлять участников,
        # так как учитываются все пользователи чата автоматически
        pass

    @classmethod
    def get_active_challenges(cls) -> list:
        """Получает список активных челленджей"""
        db = next(get_db())
        try:
            current_date = datetime.now().date()
            
            challenges = db.query(cls).filter(
                cls.start_date <= current_date,
                cls.end_date >= current_date
            ).order_by(
                cls.start_date.desc()
            ).all()
            
            return challenges
        except Exception as e:
            logger.error(f"Error getting active challenges: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    @classmethod
    def get_system_challenge(cls, chat_id, year):
        """Получает системный челлендж для чата на указанный год"""
        db = next(get_db())
        try:
            # Нормализуем chat_id
            normalized_chat_id = chat_id.replace('-100', '')
            
            logger.info(f"Looking for challenge: chat_id={normalized_chat_id}, year={year}")
            
            challenge = db.query(cls).filter(
                cls.chat_id == normalized_chat_id,
                extract('year', cls.start_date) == year,
                cls.is_system == True
            ).first()
            
            if challenge:
                logger.info(f"Found challenge: {challenge.__dict__}")
            return challenge
        except Exception as e:
            logger.error(f"Error getting system challenge: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
        finally:
            db.close()

    @classmethod
    def create(cls, title, goal_km, start_date, end_date, chat_id, is_system=False):
        """Создает новый челлендж"""
        db = next(get_db())
        try:
            challenge = cls(
                title=title,
                goal_km=goal_km,
                start_date=start_date,
                end_date=end_date,
                chat_id=chat_id,
                is_system=is_system
            )
            db.add(challenge)
            db.commit()
            db.refresh(challenge)
            return challenge
        except Exception as e:
            logger.error(f"Error creating challenge: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return None
        finally:
            db.close()

    def update_goal(self, new_goal_km):
        """Обновляет цель челленджа"""
        db = next(get_db())
        try:
            self.goal_km = new_goal_km
            db.add(self)
            db.commit()
            db.refresh(self)
            return True
        except Exception as e:
            logger.error(f"Error updating challenge goal: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return False
        finally:
            db.close()

    @classmethod
    def get_by_id(cls, challenge_id):
        """Получает челлендж по ID"""
        db = next(get_db())
        try:
            return db.query(cls).filter(cls.challenge_id == challenge_id).first()
        except Exception as e:
            logger.error(f"Error getting challenge by id: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
        finally:
            db.close()

    def get_participants_count(self) -> int:
        """Получает количество участников челленджа"""
        from database.models.running_log import RunningLog
        
        db = next(get_db())
        try:
            # Нормализуем chat_id если он есть
            normalized_chat_id = str(int(float(self.chat_id))).replace('-100', '') if self.chat_id is not None else None
            
            if self.is_system and normalized_chat_id:
                # Для системного челленджа считаем всех участников чата
                count = db.query(func.count(func.distinct(RunningLog.user_id))).filter(
                    RunningLog.chat_id == normalized_chat_id,
                    RunningLog.date_added >= self.start_date,
                    RunningLog.date_added <= self.end_date
                ).scalar()
            else:
                # Для обычного челленджа считаем только добавленных участников
                count = db.query(func.count()).filter(
                    cls.challenge_id == self.challenge_id
                ).scalar()
            
            return count or 0
        except Exception as e:
            logger.error(f"Error getting participants count: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 0
        finally:
            db.close()

    def get_total_progress(self) -> float:
        """Получает общий прогресс по челленджу"""
        from database.models.running_log import RunningLog
        
        db = next(get_db())
        try:
            # Нормализуем chat_id если он есть
            normalized_chat_id = str(int(float(self.chat_id))).replace('-100', '') if self.chat_id is not None else None
            
            if self.is_system and normalized_chat_id:
                # Для системного челленджа учитываем все пробежки в чате
                total_km = db.query(func.sum(RunningLog.km)).filter(
                    RunningLog.chat_id == normalized_chat_id,
                    RunningLog.date_added >= self.start_date,
                    RunningLog.date_added <= self.end_date
                ).scalar()
            else:
                # Для обычного челленджа учитываем только пробежки участников
                total_km = db.query(func.sum(RunningLog.km)).join(
                    cls, RunningLog.user_id == cls.user_id
                ).filter(
                    cls.challenge_id == self.challenge_id,
                    RunningLog.date_added >= self.start_date,
                    RunningLog.date_added <= self.end_date
                ).scalar()
            
            return float(total_km or 0.0)
        except Exception as e:
            logger.error(f"Error getting total progress: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 0.0
        finally:
            db.close()

    @classmethod
    def get_chat_participants(cls, chat_id):
        """Получает список участников чата"""
        from database.models.running_log import RunningLog
        
        db = next(get_db())
        try:
            # Нормализуем chat_id
            normalized_chat_id = chat_id.replace('-100', '')
            
            participants = db.query(
                RunningLog.user_id,
                func.sum(RunningLog.km).label('total_km'),
                func.count().label('runs_count')
            ).filter(
                RunningLog.chat_id == normalized_chat_id
            ).group_by(
                RunningLog.user_id
            ).all()
            
            return [{
                'user_id': p.user_id,
                'total_km': float(p.total_km or 0),
                'runs_count': p.runs_count
            } for p in participants]
        except Exception as e:
            logger.error(f"Error getting chat participants: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    def save(self):
        """Сохраняет изменения в челлендже"""
        db = next(get_db())
        try:
            db.add(self)
            db.commit()
            db.refresh(self)
            return True
        except Exception as e:
            logger.error(f"Error saving challenge: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return False
        finally:
            db.close()

    @classmethod
    def get_user_challenge(cls, user_id, year):
        """Получает челлендж пользователя на указанный год"""
        db = next(get_db())
        try:
            return db.query(cls).filter(
                cls.user_id == user_id,
                extract('year', cls.start_date) == year
            ).first()
        except Exception as e:
            logger.error(f"Error getting user challenge: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
        finally:
            db.close()

    @classmethod
    def get_chat_challenge(cls, chat_id: str, year: int) -> 'Challenge':
        """Получает челлендж чата на указанный год"""
        db = next(get_db())
        try:
            # Нормализуем chat_id
            normalized_chat_id = chat_id.replace('-100', '')
            
            return db.query(cls).filter(
                cls.chat_id == normalized_chat_id,
                extract('year', cls.start_date) == year,
                cls.is_system == True
            ).first()
        except Exception as e:
            logger.error(f"Error getting chat challenge: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
        finally:
            db.close()

    @classmethod
    def get_all_user_challenges(cls, user_id):
        """Получает все челленджи пользователя"""
        db = next(get_db())
        try:
            return db.query(cls).filter(
                cls.user_id == user_id
            ).order_by(
                cls.start_date.desc()
            ).all()
        except Exception as e:
            logger.error(f"Error getting all user challenges: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()

    @classmethod
    def clear_user_challenges(cls, user_id):
        """Удаляет все челленджи пользователя"""
        db = next(get_db())
        try:
            db.query(cls).filter(
                cls.user_id == user_id
            ).delete()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing user challenges: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return False
        finally:
            db.close()

    def get_year_progress(self):
        """Получает прогресс за год"""
        from database.models.running_log import RunningLog
        
        db = next(get_db())
        try:
            # Нормализуем chat_id если он есть
            normalized_chat_id = str(int(float(self.chat_id))).replace('-100', '') if self.chat_id is not None else None
            
            if self.is_system and normalized_chat_id:
                # Для системного челленджа учитываем все пробежки в чате
                total_km = db.query(func.sum(RunningLog.km)).filter(
                    RunningLog.chat_id == normalized_chat_id,
                    extract('year', RunningLog.date_added) == datetime.now().year
                ).scalar()
            else:
                # Для обычного челленджа учитываем только пробежки участников
                total_km = db.query(func.sum(RunningLog.km)).join(
                    cls, RunningLog.user_id == cls.user_id
                ).filter(
                    cls.challenge_id == self.challenge_id,
                    extract('year', RunningLog.date_added) == datetime.now().year
                ).scalar()
            
            return float(total_km or 0.0)
        except Exception as e:
            logger.error(f"Error getting year progress: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return 0.0
        finally:
            db.close() 