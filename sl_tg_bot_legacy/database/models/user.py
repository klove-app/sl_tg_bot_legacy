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
            # Проверяем подключение
            logger.debug("get_by_id: Checking database connection")
            connection = db.connection()
            logger.debug(f"get_by_id: Database URL: {connection.engine.url}")
            
            # Проверяем текущую базу данных
            result = connection.execute("SELECT current_database();").scalar()
            logger.debug(f"get_by_id: Current database: {result}")
            
            # Пробуем найти пользователя
            logger.debug(f"get_by_id: Creating query for user_id: {user_id}")
            query = db.query(cls)
            logger.debug(f"get_by_id: Base query: {str(query)}")
            
            # Добавляем фильтр
            query = query.filter(cls.user_id == str(user_id))
            logger.debug(f"get_by_id: Query with filter: {str(query)}")
            
            # Компилируем запрос для логов
            compiled_query = query.statement.compile(compile_kwargs={'literal_binds': True})
            logger.debug(f"get_by_id: Compiled SQL: {str(compiled_query)}")
            
            # Выполняем запрос
            logger.debug("get_by_id: Executing query...")
            user = query.first()
            logger.info(f"get_by_id: Found user: {user is not None}")
            
            if user:
                logger.debug(f"get_by_id: User details - username: {user.username}, chat_type: {user.chat_type}, user_id: {user.user_id}, type of user_id: {type(user.user_id)}")
                logger.debug(f"get_by_id: Full user object: {user.__dict__}")
            else:
                logger.debug("get_by_id: User not found in database")
                # Проверяем, есть ли пользователь напрямую через SQL
                result = connection.execute(
                    "SELECT * FROM users WHERE user_id = %s",
                    [str(user_id)]
                ).first()
                logger.debug(f"get_by_id: Direct SQL query result: {result}")
            
            return user
        except Exception as e:
            logger.error(f"get_by_id: Error during query execution: {str(e)}")
            logger.error(f"get_by_id: Full traceback: {traceback.format_exc()}")
            raise
        finally:
            if should_close:
                logger.debug("get_by_id: Closing database session")
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
            # Создаем нового пользователя
            user = cls(
                user_id=str(user_id),  # Убеждаемся, что user_id - строка
                username=username,
                chat_type=chat_type
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
            db.rollback()
            raise
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