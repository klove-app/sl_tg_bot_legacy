from sqlalchemy import create_engine
from database.base import Base
from database.models.user import User
from config.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)