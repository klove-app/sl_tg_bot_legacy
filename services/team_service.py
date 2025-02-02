from database.models.team import Team
from database.db import get_connection
from utils.formatters import round_km
from datetime import datetime

class TeamService:
    @staticmethod
    def create_team(team_name, created_by):
        return Team.create(team_name, created_by)

    @staticmethod
    def get_team_stats(team_id):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username,
                   COALESCE(SUM(r.km), 0) as total_km
            FROM users u
            JOIN team_members tm ON u.user_id = tm.user_id
            LEFT JOIN running_log r ON u.user_id = r.user_id
            WHERE tm.team_id = ?
            AND r.date_added >= date('now', '-30 days')
            GROUP BY u.username
            ORDER BY total_km DESC
        """, (team_id,))
        
        stats = cursor.fetchall()
        conn.close()
        
        return [
            {'username': row[0], 'total_km': round_km(row[1])}
            for row in stats
        ]

    @staticmethod
    def get_user_teams_stats(user_id):
        teams = Team.get_user_teams(user_id)
        return [
            {
                'team': team,
                'stats': TeamService.get_team_stats(team.team_id)
            }
            for team in teams
        ] 