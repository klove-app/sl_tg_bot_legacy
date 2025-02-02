from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base, get_db, Session, SessionLocal
from database.logger import logger
import traceback

class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String)
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.now)

    # Отношение к участникам команды
    members = relationship("TeamMember", back_populates="team")

    @classmethod
    def create(cls, team_name, created_by):
        """Создает новую команду"""
        db = next(get_db())
        try:
            team = cls(
                team_name=team_name,
                created_by=created_by,
                created_at=datetime.now()
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            return team
        except Exception as e:
            logger.error(f"Error creating team: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return None
        finally:
            db.close()

    def add_member(self, user_id):
        """Добавляет участника в команду"""
        db = next(get_db())
        try:
            member = TeamMember(
                team_id=self.team_id,
                user_id=user_id,
                joined_at=datetime.now()
            )
            db.add(member)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding team member: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            db.rollback()
            return False
        finally:
            db.close()

    @classmethod
    def get_user_teams(cls, user_id):
        """Получает список команд пользователя"""
        db = next(get_db())
        try:
            teams = db.query(cls).join(
                TeamMember, cls.team_id == TeamMember.team_id
            ).filter(
                TeamMember.user_id == user_id
            ).all()
            return teams
        except Exception as e:
            logger.error(f"Error getting user teams: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
        finally:
            db.close()


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.team_id"))
    user_id = Column(String)
    joined_at = Column(DateTime, default=datetime.now)

    # Отношение к команде
    team = relationship("Team", back_populates="members") 