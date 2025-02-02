import os
import sys
import traceback
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import base64

# Добавляем текущую директорию в PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импорты
from bot_instance import bot
from database.base import Base, engine
from database.logger import logger
import config.config as cfg

# Импортируем обработчики
from handlers.chat_handlers import register_chat_handlers
from handlers.challenge_handlers import register_handlers as register_challenge_handlers
from handlers.team_handlers import register_handlers as register_team_handlers
from handlers.stats_handlers import register_handlers as register_stats_handlers
from handlers.goal_handlers import register_handlers as register_goal_handlers
from handlers.chat_goal_handlers import register_handlers as register_chat_goal_handlers
from handlers.reset_handlers import ResetHandler
from handlers.admin_handlers import AdminHandler
from handlers.donate_handlers import DonateHandler
from handlers import message_handlers, private_handlers

class PromptGenerator:
    CARD_STYLES = [
        "cute anime style", "Disney animation style", "Pixar style", "Studio Ghibli style",
        "kawaii anime style", "cartoon style", "chibi style", "minimalist anime style"
    ]
    
    CHARACTERS = [
        "cute anime runner", "chibi athlete", "cartoon penguin in sportswear", "Studio Ghibli style runner",
        "kawaii running character", "determined anime athlete", "sporty animal character",
        "energetic chibi runner", "magical running creature"
    ]
    
    ACTIONS = [
        "running happily", "jogging with big smile", "training with joy", "sprinting through magic trail",
        "leaping over puddles", "dashing through wind", "floating while running", "running with determination"
    ]
    
    TIME_AND_WEATHER = [
        "with sakura petals falling", "under rainbow sky", "in morning sunlight", "during golden sunset",
        "under mystical twilight", "with starlit sky", "under northern lights", "with magical particles"
    ]
    
    LOCATIONS = [
        "in magical forest", "through enchanted park", "on floating islands", "in cloud kingdom",
        "through ancient forest", "on rainbow road", "in crystal canyon", "in sky garden"
    ]
    
    DECORATIONS = [
        "with anime sparkles and stars", "with kawaii decorations", "with spirit wisps",
        "with glowing butterflies", "with energy ribbons", "with floating lanterns",
        "with magical runes", "with celestial symbols"
    ]
    
    COLOR_SCHEMES = [
        "vibrant anime colors", "dreamy pastel tones", "Studio Ghibli palette",
        "ethereal harmonies", "mystic twilight colors", "enchanted palette",
        "celestial spectrum", "crystal clear tones"
    ]
    
    STYLE_ADDITIONS = [
        "anime aesthetic", "playful cartoon mood", "ethereal glow effects",
        "mystical ambiance", "enchanted atmosphere", "spiritual energy flow",
        "magical realism", "fantasy elements"
    ]
    
    @classmethod
    def generate_prompt(cls, distance):
        """Генерирует промпт для изображения на основе дистанции"""
        style = random.choice(cls.CARD_STYLES)
        character = random.choice(cls.CHARACTERS)
        action = random.choice(cls.ACTIONS)
        time_weather = random.choice(cls.TIME_AND_WEATHER)
        location = random.choice(cls.LOCATIONS)
        decoration = random.choice(cls.DECORATIONS)
        color_scheme = random.choice(cls.COLOR_SCHEMES)
        style_addition = random.choice(cls.STYLE_ADDITIONS)
        
        # Базовый промпт
        prompt = f"A {character} {action} {time_weather} {location} {decoration}, {style}, {color_scheme}, {style_addition}"
        
        # Добавляем специальные элементы в зависимости от дистанции
        if distance >= 42.2:  # Марафон
            prompt += ", epic achievement, victory pose, golden aura, triumphant atmosphere"
        elif distance >= 21.1:  # Полумарафон
            prompt += ", great achievement, triumphant pose, silver aura, proud atmosphere"
        elif distance >= 10:  # Длинная дистанция
            prompt += ", achievement, proud pose, glowing energy, determined mood"
        else:  # Любая другая дистанция
            prompt += ", joyful achievement, happy mood, positive energy, inspiring atmosphere"
            
        return prompt

def get_background_color(distance):
    """Возвращает цвет фона в зависимости от дистанции (по аналогии с поясами в киокушин карате)"""
    if distance >= 42.2:  # Марафон - черный пояс
        return (0, 0, 0, 120)
    elif distance >= 30:  # Коричневый пояс
        return (70, 40, 20, 120)
    elif distance >= 20:  # Зеленый пояс
        return (0, 100, 0, 120)
    elif distance >= 10:  # Синий пояс
        return (0, 0, 139, 120)
    else:  # Начальный уровень - светло-синий
        return (30, 144, 255, 120)

def generate_achievement_image(distance, username, date):
    """Генерирует изображение достижения с помощью Stability AI"""
    try:
        if not username:
            logger.error("Username is None or empty")
            username = "Anonymous"
        
        if not date:
            logger.error("Date is None or empty")
            date = datetime.now().strftime('%d.%m.%Y')
            
        logger.info(f"Starting image generation with parameters:")
        logger.info(f"- distance: {distance}")
        logger.info(f"- username: {username}")
        logger.info(f"- date: {date}")
        
        # Генерируем промпт
        prompt = PromptGenerator.generate_prompt(distance)
        logger.info(f"Generated prompt: {prompt}")
        
        # Формируем запрос к API
        url = f"{cfg.STABILITY_API_HOST}/v1/generation/{cfg.STABLE_DIFFUSION_ENGINE_ID}/text-to-image"
        logger.info(f"API URL: {url}")
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {cfg.STABILITY_API_KEY}"
        }
        logger.info("Headers prepared")
        
        payload = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "samples": 1,
            "steps": 30,
            "style_preset": "anime"
        }
        logger.info("Payload prepared")
        
        logger.info("Sending request to Stability AI")
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"Got response with status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Non-200 response: {response.text}")
            return None
            
        response_json = response.json()
        logger.info("Response parsed as JSON")
        
        if "artifacts" not in response_json or not response_json["artifacts"]:
            logger.error("No artifacts in response")
            logger.error(f"Response content: {response.text}")
            return None
            
        # Декодируем изображение из base64
        image_data = base64.b64decode(response_json["artifacts"][0]["base64"])
        logger.info("Image decoded from base64")
        
        # Добавляем водяной знак
        watermarked_image = add_watermark(
            image_data,
            f"{username} • {date}",  # Информация о пробежке
            "Бег: свои люди",        # Название чата
            f"{distance:.2f} км",    # Километраж
            distance                 # Для позиционирования
        )
        logger.info("Watermark added")
        
        return watermarked_image
        
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        logger.error(traceback.format_exc())
        return None

def add_watermark(image_bytes, info_text, brand_text, distance_text, distance_x):
    """Добавляет водяной знак на изображение"""
    try:
        # Открываем изображение
        image = Image.open(BytesIO(image_bytes))
        
        # Создаем объект для рисования
        draw = ImageDraw.Draw(image)
        
        # Пытаемся загрузить шрифты
        font_paths = [
            # Windows fonts
            "C:\\Windows\\Fonts\\arialbd.ttf",  # Arial Bold
            "C:\\Windows\\Fonts\\arial.ttf",    # Arial Regular
            "C:\\Windows\\Fonts\\calibrib.ttf", # Calibri Bold
            "C:\\Windows\\Fonts\\calibri.ttf",  # Calibri Regular
            "C:\\Windows\\Fonts\\segoeui.ttf",  # Segoe UI
            "C:\\Windows\\Fonts\\consola.ttf",  # Consolas Regular
            # macOS fonts
            "/System/Library/Fonts/SFNS.ttf",           # San Francisco
            "/System/Library/Fonts/Helvetica.ttc",      # Helvetica
            "/System/Library/Fonts/HelveticaNeue.ttc",  # Helvetica Neue
            "/Library/Fonts/Arial.ttf",                 # Arial
            "/Library/Fonts/Arial Bold.ttf",            # Arial Bold
        ]
        
        found_fonts = []
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    logger.info(f"Найден шрифт: {font_path}")
                    found_fonts.append(font_path)
            except Exception as e:
                logger.error(f"Ошибка при проверке шрифта {font_path}: {e}")
        
        if not found_fonts:
            logger.error("Не найдено ни одного шрифта!")
            return None
            
        # Используем первый найденный шрифт
        font_path = found_fonts[0]
        logger.info(f"Используем шрифт: {font_path}")
        
        try:
            font_large = ImageFont.truetype(font_path, 60)  # Для километража
            font_medium = ImageFont.truetype(font_path, 30)  # Для имени и даты
            font_brand = ImageFont.truetype(font_path, 50)   # Для названия чата
        except Exception as e:
            logger.error(f"Ошибка при загрузке шрифтов: {e}")
            return None
            
        # Размеры изображения
        width, height = image.size
        
        # Верхний водяной знак (название чата)
        brand_text = "Бег: свои люди"  # Заменяем название бота на название чата
        brand_bbox = draw.textbbox((0, 0), brand_text, font=font_brand)
        brand_width = brand_bbox[2] - brand_bbox[0]
        brand_height = brand_bbox[3] - brand_bbox[1]
        
        # Получаем цвет фона в зависимости от дистанции
        background_color = get_background_color(distance_x)
        
        # Полупрозрачный фон только под текстом
        padding = 20  # Отступ вокруг текста
        top_background = Image.new('RGBA', (brand_width + padding * 2, brand_height + padding * 2), background_color)
        
        # Размещаем в правом верхнем углу с отступом
        top_x = width - brand_width - padding * 3  # Дополнительный отступ справа
        top_y = padding
        image.paste(top_background, (top_x, top_y), top_background)
        
        # Рисуем название чата
        draw.text((top_x + padding, top_y + padding), brand_text, font=font_brand, fill='white')
        
        # Нижний водяной знак (имя и километраж)
        # Полупрозрачный фон для нижнего водяного знака
        bottom_background = Image.new('RGBA', (width, 80), background_color)
        image.paste(bottom_background, (0, height - 80), bottom_background)
        
        # Рисуем имя пользователя и дату слева внизу
        draw.text((20, height - 60), info_text, font=font_medium, fill='white')
        
        # Рисуем километраж справа внизу
        distance_bbox = draw.textbbox((0, 0), distance_text, font=font_large)
        distance_width = distance_bbox[2] - distance_bbox[0]
        draw.text((width - distance_width - 20, height - 70), distance_text, font=font_large, fill='white')
        
        # Сохраняем изображение
        output = BytesIO()
        image.save(output, format='PNG')
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении водяного знака: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    # Создаем таблицы в базе данных
    Base.metadata.create_all(engine)
    
    # Регистрируем обработчики
    register_chat_handlers(bot)
    register_challenge_handlers(bot)
    register_team_handlers(bot)
    register_stats_handlers(bot)
    register_goal_handlers(bot)
    register_chat_goal_handlers(bot)
    message_handlers.register_handlers(bot)
    private_handlers.register_handlers(bot)
    
    # Создаем и регистрируем обработчики
    reset_handler = ResetHandler(bot)
    reset_handler.register()
    
    admin_handler = AdminHandler(bot)
    admin_handler.register()
    
    donate_handler = DonateHandler(bot)
    donate_handler.register()
    
    logger.info("Bot handlers registered")
    logger.info("Bot is running...")
    
    # Запускаем бота
    bot.infinity_polling()