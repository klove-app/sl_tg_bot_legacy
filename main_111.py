import os
import sys
import re
import random
import traceback
import calendar
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# Добавляем текущую директорию в PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импорты
from bot_instance import bot
from database.base import Base, engine, SessionLocal
from database.logger import logger
from database.models.user import User
from database.models.running_log import RunningLog
from config.config import (
    STABLE_DIFFUSION_API_URL,
    STABLE_DIFFUSION_API_KEY,
    STABLE_DIFFUSION_ENGINE_ID
)

# Импортируем обработчики
from handlers.chat_handlers import register_chat_handlers
from handlers.challenge_handlers import register_handlers as register_challenge_handlers
from handlers.team_handlers import register_handlers as register_team_handlers
from handlers.stats_handlers import register_handlers as register_stats_handlers
from handlers.goal_handlers import register_handlers as register_goal_handlers
from handlers.base_handler import BaseHandler
from handlers.chat_goal_handlers import register_handlers as register_chat_goal_handlers
from handlers.reset_handlers import ResetHandler
from handlers.admin_handlers import AdminHandler
from handlers.donate_handlers import DonateHandler
from handlers import message_handlers, private_handlers

class PromptGenerator:
    # Стили открыток
    CARD_STYLES = [
        "Cute anime style",
        "Studio Ghibli style",
        "Cartoon style",
        "Disney animation style",
        "Pixar style",
        "Kawaii anime style",
        "Retro cartoon style",
        "Hand-drawn animation style",
        "Miyazaki inspired art",
        "Modern anime aesthetic",
        "Chibi art style",
        "Minimalist anime style",
        "Watercolor anime style"
    ]
    
    # Персонажи
    CHARACTERS = [
        "cute anime runners",
        "chibi athletes",
        "cartoon animals in sportswear",
        "funny animated penguins",
        "kawaii cats in running shoes",
        "cartoon rabbits with sport equipment",
        "animated bears in tracksuits",
        "cute anime girls running",
        "cartoon dogs jogging",
        "Studio Ghibli inspired characters",
        "determined anime athletes",
        "magical running creatures",
        "sporty forest spirits",
        "energetic chibi runners",
        "athletic animal companions"
    ]
    
    # Действия
    ACTIONS = [
        "running happily",
        "jogging with big smiles",
        "training together",
        "exercising cheerfully",
        "doing morning run",
        "racing playfully",
        "running with determination",
        "training with joy",
        "sprinting through magic trails",
        "leaping over puddles gracefully",
        "dashing through wind",
        "running with magical energy trails",
        "floating while running",
        "gliding through air"
    ]
    
    # Время суток и погода
    TIME_AND_WEATHER = [
        "at magical sunrise",
        "in anime morning light",
        "under pastel sky",
        "with sakura petals falling",
        "in dreamy daylight",
        "with sparkling morning dew",
        "under rainbow sky",
        "with magical particles floating",
        "during golden sunset",
        "in mystical twilight",
        "under starlit sky",
        "with northern lights",
        "in crystal clear morning",
        "during magical hour"
    ]
    
    # Локации
    LOCATIONS = [
        "in magical forest",
        "through anime style meadow",
        "in cherry blossom garden",
        "along mystical path",
        "through enchanted park",
        "by crystal clear lake",
        "in fantasy countryside",
        "through magical landscape",
        "in floating islands",
        "through cloud kingdom",
        "in ancient spirit forest",
        "along rainbow road",
        "through crystal canyon",
        "in sky gardens"
    ]
    
    # Декоративные элементы
    DECORATIONS = [
        "with anime sparkles and stars",
        "with magical glowing effects",
        "with floating cherry blossoms",
        "with cute cartoon hearts",
        "with magical aura",
        "with rainbow elements",
        "with kawaii decorations",
        "with magical particles",
        "with spirit wisps",
        "with glowing butterflies",
        "with energy ribbons",
        "with floating lanterns",
        "with magical runes",
        "with celestial symbols"
    ]
    
    # Цветовые схемы
    COLOR_SCHEMES = [
        "vibrant anime colors",
        "soft pastel palette",
        "Studio Ghibli color scheme",
        "bright cartoon colors",
        "magical color palette",
        "dreamy pastel tones",
        "kawaii color scheme",
        "ethereal color harmony",
        "mystic twilight colors",
        "enchanted forest palette",
        "celestial color spectrum",
        "crystal clear tones"
    ]
    
    # Стилистические добавки
    STYLE_ADDITIONS = [
        "anime aesthetic",
        "kawaii style",
        "magical atmosphere",
        "cartoon charm",
        "Studio Ghibli inspired",
        "dreamy animation style",
        "playful cartoon mood",
        "ethereal glow effect",
        "mystical ambiance",
        "enchanted atmosphere",
        "spiritual energy flow",
        "magical realism touch"
    ]
    
    @classmethod
    def generate_prompt(cls, distance: float) -> str:
        """Генерирует промпт в зависимости от дистанции"""
        import random
        
        # Базовая структура промпта
        prompt_parts = [
            random.choice(cls.CARD_STYLES),
            "illustration with",
            random.choice(cls.CHARACTERS),
            random.choice(cls.ACTIONS),
            random.choice(cls.TIME_AND_WEATHER),
            random.choice(cls.LOCATIONS) + ",",
            random.choice(cls.DECORATIONS) + ",",
            random.choice(cls.COLOR_SCHEMES) + ",",
            random.choice(cls.STYLE_ADDITIONS)
        ]
        
        # Добавляем специфичные элементы в зависимости от дистанции
        if distance >= 42.2:
            prompt_parts.insert(3, "celebrating marathon victory,")
            prompt_parts.insert(4, "wearing victory medals,")
        elif distance >= 21.1:
            prompt_parts.insert(3, "celebrating half marathon achievement,")
            prompt_parts.insert(4, "with runner medals,")
        elif distance >= 10:
            prompt_parts.insert(3, "on a long distance adventure,")
        
        # Собираем промпт
        return " ".join(prompt_parts)
    
    @classmethod
    def get_prompt(cls, distance: float) -> str:
        """Возвращает сгенерированный промпт для указанной дистанции"""
        import random
        # Генерируем три варианта и выбираем случайный
        prompts = [cls.generate_prompt(distance) for _ in range(3)]
        return random.choice(prompts)

def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Starting bot...")
        
        # Создаем таблицы в базе данных
        Base.metadata.create_all(engine)
        logger.info("Database tables created")
        
        # Регистрируем обработчики
        logger.info("Starting handlers registration...")
        
        try:
            message_handlers.register_handlers(bot)
            logger.info("Message handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register message handlers: {e}")
            raise
        
        try:
            register_chat_handlers(bot)
            logger.info("Chat handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register chat handlers: {e}")
            raise
        
        try:
            register_challenge_handlers(bot)
            logger.info("Challenge handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register challenge handlers: {e}")
            raise
        
        try:
            register_team_handlers(bot)
            logger.info("Team handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register team handlers: {e}")
            raise
        
        try:
            register_stats_handlers(bot)
            logger.info("Stats handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register stats handlers: {e}")
            raise
        
        try:
            register_goal_handlers(bot)
            logger.info("Goal handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register goal handlers: {e}")
            raise
        
        try:
            register_chat_goal_handlers(bot)
            logger.info("Chat goal handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register chat goal handlers: {e}")
            raise
        
        try:
            AdminHandler(bot).register()
            logger.info("Admin handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register admin handlers: {e}")
            raise
        
        try:
            ResetHandler(bot).register()
            logger.info("Reset handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register reset handlers: {e}")
            raise
        
        try:
            DonateHandler(bot).register()
            logger.info("Donate handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register donate handlers: {e}")
            raise
        
        logger.info("All handlers registered successfully")
        
        # Запускаем бота с расширенными настройками
        logger.info("Starting bot polling...")
        bot.infinity_polling(timeout=20, long_polling_timeout=20, 
                           allowed_updates=["message", "edited_message", "callback_query"])
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()