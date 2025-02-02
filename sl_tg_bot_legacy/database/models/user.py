from sqlalchemy import Column, String, Float, Boolean, REAL
from sqlalchemy.orm import Session, relationship
from database.base import Base, get_db

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
        if db is None:
            db = next(get_db())
            should_close = True
        else:
            should_close = False
            
        try:
            return db.query(cls).filter(cls.user_id == user_id).first()
        finally:
            if should_close:
                db.close()

    @classmethod
    def create(cls, user_id: str, username: str, chat_type: str = 'group') -> 'User':
        """Создать нового пользователя"""
        db = next(get_db())
        user = cls(user_id=user_id, username=username, chat_type=chat_type)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

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