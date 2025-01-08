from services.team_service import TeamService

def register_handlers(bot):
    @bot.message_handler(commands=['createteam'])
    def create_team(message):
        try:
            team_name = ' '.join(message.text.split()[1:])
            if not team_name:
                bot.reply_to(message, "Пожалуйста, укажите название команды: /createteam [название]")
                return

            user_id = str(message.from_user.id)
            team = TeamService.create_team(team_name, user_id)
            
            response = f"Команда '{team_name}' успешно создана!\n"
            response += f"ID команды: {team.team_id}"
            
            bot.reply_to(message, response)
            
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка: {str(e)}")

    @bot.message_handler(commands=['teamstats'])
    def team_stats(message):
        try:
            user_id = str(message.from_user.id)
            teams_stats = TeamService.get_user_teams_stats(user_id)
            
            if not teams_stats:
                bot.reply_to(message, "Вы не состоите ни в одной команде")
                return
                
            response = "📊 Статистика команд:\n\n"
            
            for team_data in teams_stats:
                team = team_data['team']
                stats = team_data['stats']
                
                response += f"👥 Команда: {team.team_name}\n"
                response += "Статистика за последние 30 дней:\n"
                
                for member in stats:
                    response += f"🏃‍♂️ {member['username']}: {member['total_km']} км\n"
                
                response += "\n"
            
            bot.reply_to(message, response)
            
        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка: {str(e)}") 