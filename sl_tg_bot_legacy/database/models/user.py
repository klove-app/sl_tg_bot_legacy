from sqlalchemy import Column, String, Float, Boolean, REAL
from sqlalchemy.orm import Session, relationship
from database.base import Base, get_db
from database.logger import logger

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    username = Column(String)
    yearly_goal = Column(REAL, nullable=True)
    yearly_progress = Column(REAL, nullable=True)
    goal_km = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    chat_type = Column(String, default='group')  # 'private' или 'group'

    # Отношение к пробежкам
    runs = relationship("RunningLog", back_populates="user")

    @classmethod
    def get_by_id(cls, user_id: str, db = None) -> 'User':
        """Получить пользователя по ID"""
        logger.info(f"get_by_id: Looking for user with ID {user_id}")
        logger.info(f"get_by_id: Type of user_id: {type(user_id)}")
        
        if db is None:
            logger.debug("get_by_id: Creating new database session")
            db = next(get_db())
            should_close = True
        else:
            logger.debug("get_by_id: Using existing database session")
            should_close = False
            
        try:
            query = db.query(cls).filter(cls.user_id == user_id)
            logger.debug(f"get_by_id: Executing query: {str(query.statement.compile(compile_kwargs={'literal_binds': True}))}")
            user = query.first()
            logger.info(f"get_by_id: Found user: {user is not None}")
            if user:
                logger.debug(f"get_by_id: User details - username: {user.username}, chat_type: {user.chat_type}, user_id: {user.user_id}, type of user_id: {type(user.user_id)}")
            return user
        finally:
            if should_close:
                logger.debug("get_by_id: Closing database session")
                db.close()

    @classmethod
    def create(cls, user_id: str, username: str, chat_type: str = 'group', db = None) -> 'User':
        """Создать нового пользователя"""
        if db is None:
            db = next(get_db())
            should_close = True
        else:
            should_close = False
            
        try:
            # Сначала проверяем, не существует ли уже пользователь
            existing_user = db.query(cls).filter(cls.user_id == user_id).first()
            if existing_user:
                return existing_user
                
            user = cls(user_id=user_id, username=username, chat_type=chat_type)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            if should_close:
                db.close()

    def save(self):
        """Сохранить изменения пользователя"""
        db = next(get_db())
        db.add(self)
        db.commit()
        db.refresh(self)

    def update(self, **kwargs):
        """Обновить атрибуты пользователя"""
        db = next(get_db())
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.add(self)
        db.commit()
        db.refresh(self)

    def is_private(self) -> bool:
        """Проверить, является ли пользователь индивидуальным"""
        return self.chat_type == 'private' 