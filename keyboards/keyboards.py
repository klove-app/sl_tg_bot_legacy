from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('/stats', '/top')
    markup.row('/challenges', '/mychallenges')
    markup.row('/teamstats', '/history')
    markup.row('/help')
    return markup

def get_challenge_keyboard(challenge_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(f'/joinchallenge {challenge_id}', f'/challengestats {challenge_id}')
    markup.row('/challenges', '/mychallenges')
    return markup

def get_team_keyboard(team_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(f'/jointeam {team_id}', f'/teamstats')
    markup.row('/createteam', '/help')
    return markup 