from database.db import get_connection
from datetime import datetime

class Team:
    def __init__(self, team_id, team_name, created_by, created_at):
        self.team_id = team_id
        self.team_name = team_name
        self.created_by = created_by
        self.created_at = created_at

    @staticmethod
    def create(team_name, created_by):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO teams (team_name, created_by, created_at)
            VALUES (?, ?, ?)
        """, (team_name, created_by, datetime.now()))
        
        team_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return Team(team_id, team_name, created_by, datetime.now())

    def add_member(self, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, joined_at)
            VALUES (?, ?, ?)
        """, (self.team_id, user_id, datetime.now()))
        
        conn.commit()
        conn.close()

    @staticmethod
    def get_user_teams(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.* FROM teams t
            JOIN team_members tm ON t.team_id = tm.team_id
            WHERE tm.user_id = ?
        """, (user_id,))
        
        teams = cursor.fetchall()
        conn.close()
        
        return [Team(t[0], t[1], t[2], t[3]) for t in teams] 