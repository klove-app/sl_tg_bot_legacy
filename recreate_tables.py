from sqlalchemy import create_engine
from database.base import Base
from database.models.user import User

engine = create_engine('sqlite:///bot.db')
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)