from sqlalchemy import Column, Integer, String, Float, Boolean, REAL, Text
from sqlalchemy.orm import Session, relationship
from database.base import Base, get_db
from database.logger import logger
import traceback

class User(Base):
    __tablename__ = "users"

    user_id = Column(Text, primary_key=True, index=True)
    username = Column(Text)
    yearly_goal = Column(REAL, nullable=True)
    yearly_progress = Column(REAL, nullable=True)
    goal_km = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    chat_type = Column(Text, default='group')  # 'private' или 'group'

    # Отношение к пробежкам
    runs = relationship("RunningLog", back_populates="user")

    @staticmethod
    def _normalize_user_id(user_id) -> str:
        """Нормализует ID пользователя"""
        original_id = user_id
        normalized_id = str(user_id).strip()
        logger.debug(f"Normalizing user_id: original='{original_id}' ({type(original_id)}) -> normalized='{normalized_id}' ({type(normalized_id)})")
        return normalized_id

    @classmethod
    def get_by_id(cls, user_id: str, db = None) -> 'User':
        """Получить пользователя по ID"""
        logger.debug(f"get_by_id called with user_id='{user_id}' ({type(user_id)})")
        
        if db is None:
            db = next(get_db())
            should_close = True
            logger.debug("Created new database session")
        else:
            should_close = False
            logger.debug("Using existing database session")
            
        try:
            normalized_id = cls._normalize_user_id(user_id)
            logger.debug(f"Searching for user with normalized_id='{normalized_id}'")
            
            # Проверяем соединение с базой
            try:
                db.execute("SELECT 1")
                logger.debug("Database connection is alive")
            except Exception as e:
                logger.error(f"Database connection error: {e}")
                raise
            
            # Пробуем разные варианты поиска
            result = None
            
            # 1. Стандартный поиск через ORM
            result = db.query(cls).filter(cls.user_id == normalized_id).first()
            logger.debug(f"ORM search result: {result}")
            
            if not result:
                # 2. Поиск через CAST
                sql = f"SELECT * FROM users WHERE CAST(user_id AS TEXT) = CAST('{normalized_id}' AS TEXT)"
                raw_result = db.execute(sql).fetchone()
                logger.debug(f"Raw SQL with CAST result: {raw_result}")
                
                if raw_result:
                    # Если нашли через SQL, но не через ORM - создаем объект
                    result = cls()
                    for idx, col in enumerate(raw_result.keys()):
                        setattr(result, col, raw_result[idx])
                    logger.info(f"Created user object from raw SQL result: {result.user_id}, {result.username}")
            
            if result:
                logger.info(f"Found user: {result.user_id}, {result.username}")
            else:
                logger.info(f"User not found: {normalized_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_by_id: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        finally:
            if should_close:
                logger.debug("Closing database session")
                db.close()

    @classmethod
    def create(cls, user_id: str, username: str, chat_type: str = 'group', db = None) -> 'User':
        """Создать нового пользователя"""
        logger.info(f"create: Creating new user with ID {user_id}")
        
        if db is None:
            logger.debug("create: Creating new database session")
            db = next(get_db())
            should_close = True
        else:
            logger.debug("create: Using existing database session")
            should_close = False
            
        try:
            # Нормализуем данные
            normalized_user_id = cls._normalize_user_id(user_id)
            normalized_username = str(username).strip() if username else f"user_{normalized_user_id}"
            normalized_chat_type = str(chat_type).strip().lower()
            
            # Проверяем, существует ли уже пользователь
            existing_user = cls.get_by_id(normalized_user_id, db=db)
            if existing_user:
                logger.info(f"create: User {normalized_user_id} already exists, updating")
                existing_user.username = normalized_username
                existing_user.chat_type = normalized_chat_type
                db.add(existing_user)
                db.commit()
                db.refresh(existing_user)
                return existing_user
            
            # Создаем нового пользователя
            user = cls(
                user_id=normalized_user_id,
                username=normalized_username,
                chat_type=normalized_chat_type,
                yearly_goal=0,
                yearly_progress=0,
                goal_km=0,
                is_active=True
            )
            logger.debug(f"create: Adding user to session")
            db.add(user)
            db.commit()
            logger.debug(f"create: User committed to database")
            db.refresh(user)
            logger.info(f"create: User created successfully")
            return user
        except Exception as e:
            logger.error(f"create: Error creating user: {e}")
            logger.error(f"create: Full traceback: {traceback.format_exc()}")
            db.rollback()
            return None
        finally:
            if should_close:
                logger.debug("create: Closing database session")
                db.close()

    def save(self):
        """Сохранить изменения пользователя"""
        db = next(get_db())
        try:
            db.add(self)
            db.commit()
            db.refresh(self)
        finally:
            db.close()

    def update(self, **kwargs):
        """Обновить атрибуты пользователя"""
        db = next(get_db())
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db.add(self)
            db.commit()
            db.refresh(self)
        finally:
            db.close()

    def is_private(self) -> bool:
        """Проверить, является ли пользователь индивидуальным"""
        return self.chat_type == 'private' 