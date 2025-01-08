from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.orm import Session, relationship
from database.base import Base, get_db

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    username = Column(String)
    goal_km = Column(Float, default=0)
    is_active = Column(Boolean, default=True)

    # Отношение к пробежкам
    runs = relationship("RunningLog", back_populates="user")

    @classmethod
    def get_by_id(cls, user_id: str) -> 'User':
        """Получить пользователя по ID"""
        db = next(get_db())
        return db.query(cls).filter(cls.user_id == user_id).first()

    @classmethod
    def create(cls, user_id: str, username: str) -> 'User':
        """Создать нового пользователя"""
        db = next(get_db())
        user = cls(user_id=user_id, username=username)
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