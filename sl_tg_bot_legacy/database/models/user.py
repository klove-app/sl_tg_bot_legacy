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
            
            # Сначала проверим прямым SQL запросом
            sql = "SELECT * FROM users WHERE user_id = :user_id"
            params = {"user_id": normalized_id}
            logger.debug(f"Executing raw SQL: {sql} with params: {params}")
            raw_result = db.execute(sql, params).fetchone()
            logger.debug(f"Raw SQL result: {raw_result}")
            
            if raw_result:
                logger.debug(f"Found user with raw SQL: {dict(raw_result)}")
                # Создаем объект из результата
                result = cls()
                for key, value in dict(raw_result).items():
                    setattr(result, key, value)
                logger.debug(f"Created user object: {vars(result)}")
                return result
            
            # Если прямой SQL не нашел, пробуем через ORM
            logger.debug("Trying ORM query")
            query = db.query(cls).filter(cls.user_id == normalized_id)
            logger.debug(f"ORM query: {str(query)}")
            result = query.first()
            logger.debug(f"ORM query result: {result}")
            
            if result:
                logger.info(f"Found user via ORM: {result.user_id}, {result.username}")
            else:
                logger.info(f"User not found: {normalized_id}")
                # Проверяем, есть ли похожие ID
                similar_query = db.query(cls.user_id).filter(cls.user_id.like(f"%{normalized_id}%"))
                logger.debug(f"Similar IDs query: {str(similar_query)}")
                similar_ids = [r[0] for r in similar_query.all()]
                if similar_ids:
                    logger.debug(f"Found similar user_ids: {similar_ids}")
            
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
        logger.info(f"create: Creating new user with ID {user_id} ({type(user_id)})")
        
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
            
            logger.debug(f"create: Normalized data - user_id='{normalized_user_id}', username='{normalized_username}', chat_type='{normalized_chat_type}'")
            
            # Проверяем, существует ли уже пользователь
            existing_user = cls.get_by_id(normalized_user_id, db=db)
            logger.debug(f"create: Checking for existing user: {existing_user}")
            
            if existing_user:
                logger.info(f"create: User {normalized_user_id} already exists, updating")
                existing_user.username = normalized_username
                existing_user.chat_type = normalized_chat_type
                db.add(existing_user)
                db.commit()
                db.refresh(existing_user)
                logger.debug(f"create: Updated existing user: {existing_user.user_id}, {existing_user.username}")
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
            logger.debug(f"create: Created new user object: {user.user_id}, {user.username}")
            
            # Проверяем соединение с базой
            try:
                db.execute("SELECT 1")
                logger.debug("create: Database connection is alive")
            except Exception as e:
                logger.error(f"create: Database connection error: {e}")
                raise
            
            logger.debug(f"create: Adding user to session")
            db.add(user)
            db.commit()
            logger.debug(f"create: User committed to database")
            db.refresh(user)
            logger.info(f"create: User created successfully: {user.user_id}, {user.username}")
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

    @classmethod
    def find_by_id_raw(cls, user_id: str, db = None) -> dict:
        """Поиск пользователя через прямой SQL запрос"""
        logger.debug(f"find_by_id_raw called with user_id='{user_id}' ({type(user_id)})")
        
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
            
            # Прямой SQL запрос
            sql = """
            SELECT user_id, username, yearly_goal, yearly_progress, goal_km, is_active, chat_type
            FROM users 
            WHERE user_id = :user_id
            """
            result = db.execute(sql, {"user_id": normalized_id}).fetchone()
            logger.debug(f"Raw SQL search result: {result}")
            
            if result:
                # Преобразуем результат в словарь
                user_dict = dict(zip(result.keys(), result))
                logger.debug(f"Converted to dict: {user_dict}")
                return user_dict
            else:
                logger.debug("User not found with raw SQL")
                return None
                
        except Exception as e:
            logger.error(f"Error in find_by_id_raw: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        finally:
            if should_close:
                logger.debug("Closing database session")
                db.close() 