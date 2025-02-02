from bot_instance import bot
from telebot import types
from database.logger import logger
from database.models.user import User
from database.models.challenge import Challenge
from datetime import datetime

# Словарь для хранения временных данных пользователей
user_data = {} 