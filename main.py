import os
import sys
import re
import traceback
import calendar
import random
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import base64

# Добавляем текущую директорию в PATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Импорты
from bot_instance import bot
from database.base import Base, engine, SessionLocal
from database.logger import logger
from database.models.user import User
from database.models.running_log import RunningLog
import config.config as cfg

# Используем переменные из конфига
TOKEN = cfg.TOKEN
ADMIN_IDS = cfg.ADMIN_IDS
DATABASE_NAME = cfg.DATABASE_NAME
DATABASE_URL = cfg.DATABASE_URL
STABILITY_API_HOST = cfg.STABILITY_API_HOST
STABILITY_API_KEY = cfg.STABILITY_API_KEY
STABLE_DIFFUSION_ENGINE_ID = cfg.STABLE_DIFFUSION_ENGINE_ID

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

def add_watermark(image_bytes, info_text, brand_text, distance_text, distance_x):
    """Добавляет водяной знак на изображение"""
    try:
        # Открываем изображение
        image = Image.open(BytesIO(image_bytes))
        
        # Создаем объект для рисования
        draw = ImageDraw.Draw(image)
        
        # Пытаемся загрузить шрифты
        font_paths = [
            # Windows
            "C:\\Windows\\Fonts\\arialbd.ttf",  # Arial Bold
            "C:\\Windows\\Fonts\\arial.ttf",    # Arial Regular
            "C:\\Windows\\Fonts\\calibrib.ttf", # Calibri Bold
            "C:\\Windows\\Fonts\\calibri.ttf",  # Calibri Regular
            "C:\\Windows\\Fonts\\segoeui.ttf",  # Segoe UI
            "C:\\Windows\\Fonts\\consola.ttf",  # Consolas Regular
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
        
        # Полупрозрачный фон только под текстом
        padding = 20  # Отступ вокруг текста
        top_background = Image.new('RGBA', (brand_width + padding * 2, brand_height + padding * 2), (0, 0, 0, 120))
        
        # Размещаем в правом верхнем углу с отступом
        top_x = width - brand_width - padding * 3  # Дополнительный отступ справа
        top_y = padding
        image.paste(top_background, (top_x, top_y), top_background)
        
        # Рисуем название чата
        draw.text((top_x + padding, top_y + padding), brand_text, font=font_brand, fill='white')
        
        # Нижний водяной знак (имя и километраж)
        # Полупрозрачный фон для нижнего водяного знака
        bottom_background = Image.new('RGBA', (width, 80), (0, 0, 0, 120))
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
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        logger.info(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API request failed with status code: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return None
            
        # Получаем JSON из ответа
        response_json = response.json()
        logger.info("Response received and parsed")
        
        # Проверяем наличие артефактов в ответе
        if 'artifacts' not in response_json or not response_json['artifacts']:
            logger.error("No artifacts in response")
            return None
            
        try:
            # Декодируем изображение из base64
            logger.info("Decoding image from base64")
            image_bytes = base64.b64decode(response_json['artifacts'][0]['base64'])
            logger.info("Image decoded successfully")
            
            # Форматируем текст для водяного знака
            info_text = f"{username} • {date}"
            distance_text = f"{distance:.1f} км"
            distance_x = 0
            
            # Добавляем водяной знак
            logger.info("Adding watermark")
            final_image = add_watermark(image_bytes, info_text, "Бег: свои люди", distance_text, distance_x)
            logger.info("Watermark added successfully")
            
            return final_image
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            logger.error(traceback.format_exc())
            return None
            
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        logger.error(traceback.format_exc())
        return None

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

class MessageHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики текстовых сообщений"""
        self.logger.info("Registering message handlers")
        
        # Регистрируем обработчик текстовых сообщений
        self.bot.register_message_handler(
            self.handle_text,
            content_types=['text'],
            func=lambda message: (
                message.chat.type == 'private' or
                (self.bot.get_me().username and f"@{self.bot.get_me().username}" in message.text)
            )
        )
        
        # Регистрируем обработчик фото
        self.bot.register_message_handler(
            self.handle_photo_run,
            content_types=['photo']
        )
        
        self.logger.info("Message handlers registered successfully")

    def handle_text(self, message):
        """Обработчик текстовых сообщений"""
        self.logger.info(f"Processing message: {message.text}")
        self.logger.info(f"Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
        
        # Проверяем, что сообщение адресовано боту
        is_bot_mentioned = False
        if message.reply_to_message and message.reply_to_message.from_user.id == self.bot.get_me().id:
            is_bot_mentioned = True
        elif self.bot.get_me().username and f"@{self.bot.get_me().username}" in message.text:
            is_bot_mentioned = True
        elif message.chat.type == 'private':
            is_bot_mentioned = True
            
        # Если сообщение не адресовано боту - игнорируем
        if not is_bot_mentioned:
            return
        
        # Проверяем, содержит ли сообщение число
        try:
            # Извлекаем первое число из сообщения, поддерживая целые и дробные числа
            first_word = message.text.split()[0]
            # Пробуем сначала преобразовать как есть (для целых чисел)
            try:
                km = float(first_word)
            except ValueError:
                # Если не получилось, пробуем заменить запятую на точку (для дробных)
                km = float(first_word.replace(',', '.'))
            
            self.logger.info(f"Extracted distance: {km} km")
            
            if km <= 0:
                self.logger.warning(f"Invalid distance: {km} km")
                self.bot.reply_to(
                    message,
                    "⚠️ *Некорректная дистанция*\n\n"
                    "Пожалуйста, укажите положительное число километров",
                    parse_mode='Markdown'
                )
                return
                
            user_id = str(message.from_user.id)
            chat_id = str(message.chat.id)
            chat_type = message.chat.type
            
            self.logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Chat Type: {chat_type}")
            
            # Получаем или создаем пользователя
            user = User.get_by_id(user_id)
            self.logger.debug(f"Found user: {user}")
            
            if not user:
                username = message.from_user.username or message.from_user.first_name
                self.logger.info(f"Creating new user: {username}")
                user = User.create(user_id=user_id, username=username)
                self.logger.info(f"Created new user: {username} ({user_id})")
            
            # Добавляем запись о пробежке
            self.logger.info(f"Adding run entry: {km} km")
            success = RunningLog.add_entry(
                user_id=user_id,
                km=km,
                date_added=datetime.now().date(),
                notes=message.text,
                chat_id=chat_id,
                chat_type=chat_type
            )
            
            if success:
                self.logger.info("Run entry added successfully")
                # Получаем статистику
                total_km = RunningLog.get_user_total_km(user_id)
                self.logger.debug(f"Total km: {total_km}")
                
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                year_stats = RunningLog.get_user_stats(user_id, current_year)
                self.logger.debug(f"Year stats: {year_stats}")
                
                month_stats = RunningLog.get_user_stats(user_id, current_year, current_month)
                self.logger.debug(f"Month stats: {month_stats}")
                
                # Формируем ответное сообщение
                response = (
                    f"🎉 *Новая пробежка записана!*\n"
                    f"📍 {km:.1f} км\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                    
                    f"📊 *Статистика {calendar.month_name[datetime.now().month]}*\n"
                    f"🏃 {month_stats['runs_count']} пробежек\n"
                    f"📏 {month_stats['total_km']:.1f} км всего\n"
                    f"⌀ {month_stats['avg_km']:.1f} км в среднем\n\n"
                    
                    f"📈 *Статистика {datetime.now().year}*\n"
                    f"🏃 {year_stats['runs_count']} пробежек\n"
                    f"📏 {year_stats['total_km']:.1f} км всего\n"
                    f"⌀ {year_stats['avg_km']:.1f} км в среднем"
                )
                
                # Добавляем информацию о годовой цели, если она установлена
                if user.goal_km and user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                    remaining = user.goal_km - total_km
                    response += (
                        f"\n\n🎯 *Годовая цель*\n"
                        f"🎪 {user.goal_km:.0f} км\n"
                        f"▸ {progress_bar} {progress:.1f}%\n"
                        f"📍 Осталось: {remaining:.1f} км"
                    )
                else:
                    response += (
                        f"\n\n💡 Установите годовую цель командой /setgoal"
                    )
                
                # Добавляем мотивационное сообщение
                if km > 10:
                    response += "\n\n🔥 Отличная длительная пробежка!"
                elif km > 5:
                    response += "\n\n💪 Хорошая тренировка!"
                else:
                    response += "\n\n👍 Так держать!"
                
                # Для длинных дистанций генерируем изображение
                if km >= 10:
                    try:
                        image_data = generate_achievement_image(km, username, datetime.now().strftime('%d.%m.%Y'))
                        if image_data:
                            photo = BytesIO(image_data)
                            photo.name = 'achievement.png'
                            self.bot.send_photo(
                                message.chat.id,
                                photo,
                                caption=response,
                                parse_mode='Markdown',
                                reply_to_message_id=message.message_id
                            )
                        else:
                            self.bot.reply_to(message, response, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Error generating image: {e}")
                        self.bot.reply_to(message, response, parse_mode='Markdown')
                else:
                    self.bot.reply_to(message, response, parse_mode='Markdown')
                
                self.logger.info(f"Logged run: {km}km for user {user_id}")
                
            else:
                self.logger.error(f"Failed to save run for user {user_id}")
                error_message = (
                    "⚠️ *Не удалось сохранить пробежку*\n\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору"
                )
                self.bot.reply_to(message, error_message, parse_mode='Markdown')
            return
                
        except ValueError:
            self.logger.warning(f"Invalid message format: {message.text}")
            self.bot.reply_to(
                message,
                "⚠️ *Некорректный формат*\n\n"
                "Пример: `5.2` или `5,2`",
                parse_mode='Markdown'
            )
            return
        except Exception as e:
            self.logger.error(f"Error saving run: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            error_message = (
                "😔 *Произошла ошибка*\n\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору"
            )
            self.bot.reply_to(message, error_message, parse_mode='Markdown')
            return
            
        # Если сообщение в личном чате и не содержит число
        if message.chat.type == 'private':
            help_message = (
                "*📝 Как записать пробежку:*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "*1.* Просто отправьте километраж:\n"
                "• Пример: `5.2`\n\n"
                "*2.* Добавьте описание:\n"
                "• Пример: `5.2 Утренняя пробежка`\n\n"
                "*3.* Отправьте фото с подписью:\n"
                "• Добавьте к фото текст с километражем\n\n"
                "🔍 Все команды: /help"
            )
            self.bot.reply_to(message, help_message, parse_mode='Markdown')

    def handle_photo_run(self, message):
        """Обработчик фотографий с подписью"""
        self.logger.info(f"Processing photo message with caption: {message.caption}")
        self.logger.info(f"Chat type: {message.chat.type}, Chat ID: {message.chat.id}")
        
        # Проверяем, что фото адресовано боту
        is_bot_mentioned = False
        if message.reply_to_message and message.reply_to_message.from_user.id == self.bot.get_me().id:
            is_bot_mentioned = True
        elif self.bot.get_me().username and message.caption and f"@{self.bot.get_me().username}" in message.caption:
            is_bot_mentioned = True
        elif message.chat.type == 'private':
            is_bot_mentioned = True
            
        # Если фото не адресовано боту - игнорируем
        if not is_bot_mentioned:
            return
        
        if not message.caption:
            self.logger.warning("No caption provided with photo")
            self.bot.reply_to(
                message,
                "⚠️ *Добавьте подпись с километражем*\n\n"
                "Пример: `5.2` или `5.2 Утренняя пробежка`",
                parse_mode='Markdown'
            )
            return
            
        try:
            # Извлекаем первое число из подписи, поддерживая целые и дробные числа
            first_word = message.caption.split()[0]
            # Пробуем сначала преобразовать как есть (для целых чисел)
            try:
                km = float(first_word)
            except ValueError:
                # Если не получилось, пробуем заменить запятую на точку (для дробных)
                km = float(first_word.replace(',', '.'))
            
            self.logger.info(f"Extracted distance from caption: {km} km")
            
            if km <= 0:
                self.logger.warning(f"Invalid distance: {km} km")
                self.bot.reply_to(
                    message,
                    "⚠️ *Некорректная дистанция*\n\n"
                    "Пожалуйста, укажите положительное число километров",
                    parse_mode='Markdown'
                )
                return
                
            user_id = str(message.from_user.id)
            chat_id = str(message.chat.id)
            chat_type = message.chat.type
            
            self.logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Chat Type: {chat_type}")
            
            # Получаем или создаем пользователя
            user = User.get_by_id(user_id)
            self.logger.debug(f"Found user: {user}")
            
            if not user:
                username = message.from_user.username or message.from_user.first_name
                self.logger.info(f"Creating new user: {username}")
                user = User.create(user_id=user_id, username=username)
                self.logger.info(f"Created new user: {username} ({user_id})")
            
            # Добавляем запись о пробежке
            self.logger.info(f"Adding run entry with photo: {km} km")
            success = RunningLog.add_entry(
                user_id=user_id,
                km=km,
                date_added=datetime.now().date(),
                notes=message.caption,
                chat_id=chat_id,
                chat_type=chat_type
            )
            
            if success:
                self.logger.info("Run entry with photo added successfully")
                # Получаем статистику
                total_km = RunningLog.get_user_total_km(user_id)
                self.logger.debug(f"Total km: {total_km}")
                
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                year_stats = RunningLog.get_user_stats(user_id, current_year)
                self.logger.debug(f"Year stats: {year_stats}")
                
                month_stats = RunningLog.get_user_stats(user_id, current_year, current_month)
                self.logger.debug(f"Month stats: {month_stats}")
                
                # Формируем ответное сообщение
                response = (
                    f"🎉 *Пробежка с фото записана!*\n"
                    f"📍 {km:.1f} км\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
                    
                    f"📊 *Статистика {calendar.month_name[datetime.now().month]}*\n"
                    f"🏃 {month_stats['runs_count']} пробежек\n"
                    f"📏 {month_stats['total_km']:.1f} км всего\n"
                    f"⌀ {month_stats['avg_km']:.1f} км в среднем\n\n"
                    
                    f"📈 *Статистика {datetime.now().year}*\n"
                    f"🏃 {year_stats['runs_count']} пробежек\n"
                    f"📏 {year_stats['total_km']:.1f} км всего\n"
                    f"⌀ {year_stats['avg_km']:.1f} км в среднем"
                )
                
                # Добавляем информацию о годовой цели, если она установлена
                if user.goal_km and user.goal_km > 0:
                    progress = (total_km / user.goal_km * 100)
                    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
                    remaining = user.goal_km - total_km
                    response += (
                        f"\n\n🎯 *Годовая цель*\n"
                        f"🎪 {user.goal_km:.0f} км\n"
                        f"▸ {progress_bar} {progress:.1f}%\n"
                        f"📍 Осталось: {remaining:.1f} км"
                    )
                else:
                    response += (
                        f"\n\n💡 Установите годовую цель командой /setgoal"
                    )
                
                # Добавляем мотивационное сообщение
                if km > 10:
                    response += "\n\n🔥 Отличная длительная пробежка!"
                elif km > 5:
                    response += "\n\n💪 Хорошая тренировка!"
                else:
                    response += "\n\n👍 Так держать!"
                
                # Для длинных дистанций генерируем изображение
                if km >= 10:
                    try:
                        image_data = generate_achievement_image(km, username, datetime.now().strftime('%d.%m.%Y'))
                        if image_data:
                            photo = BytesIO(image_data)
                            photo.name = 'achievement.png'
                            self.bot.send_photo(
                                message.chat.id,
                                photo,
                                caption=response,
                                parse_mode='Markdown',
                                reply_to_message_id=message.message_id
                            )
                        else:
                            self.bot.reply_to(message, response, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Error generating image: {e}")
                        self.bot.reply_to(message, response, parse_mode='Markdown')
                else:
                    self.bot.reply_to(message, response, parse_mode='Markdown')
                
                self.logger.info(f"Logged run with photo: {km}km for user {user_id}")
            else:
                self.logger.error(f"Failed to save run with photo for user {user_id}")
                error_message = (
                    "⚠️ *Не удалось сохранить пробежку*\n\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору"
                )
                self.bot.reply_to(message, error_message, parse_mode='Markdown')
            return
                
        except ValueError:
            self.logger.warning(f"Invalid caption format: {message.caption}")
            self.bot.reply_to(
                message,
                "⚠️ *Некорректный формат числа*\n\n"
                "Используйте точку или запятую\n"
                "Пример: `5.2` или `5,2`",
                parse_mode='Markdown'
            )
        except Exception as e:
            self.logger.error(f"Error in handle_photo_run: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            error_message = (
                "😔 *Произошла ошибка*\n\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору"
            )
            self.bot.reply_to(message, error_message, parse_mode='Markdown')

    def handle_profile(self, message: Message, user_id=None):
        """Показывает личный кабинет пользователя"""
        self.log_message(message, "profile")
        try:
            # Если user_id не передан, берем из сообщения
            if user_id is None:
                user_id = str(message.from_user.id)
            
            # Используем переданную сессию или создаем новую
            db = SessionLocal()
            try:
                # Получаем или создаем пользователя
                user = db.query(User).filter(User.user_id == user_id).first()
                if not user:
                    username = message.from_user.username or message.from_user.first_name
                    user = User(user_id=user_id, username=username)
                    db.add(user)
                    db.commit()
                
                current_year = datetime.now().year
                current_month = datetime.now().month
                
                # Получаем статистику
                year_stats = RunningLog.get_user_stats(user_id, current_year, db=db)
                month_stats = RunningLog.get_user_stats(user_id, current_year, current_month, db=db)
                best_stats = RunningLog.get_best_stats(user_id, db=db)
                
                # Формируем профиль с HTML-форматированием
                response = f"<b>👤 Профиль {user.username}</b>\n\n"
                
                # Прогресс к цели
                if user.goal_km > 0:
                    progress = (year_stats['total_km'] / user.goal_km * 100)
                    progress_bar = self._generate_progress_bar(progress)
                    response += f"🎯 Цель на {current_year}: {user.goal_km:.2f} км\n"
                    response += f"{progress_bar} {progress:.2f}%\n"
                    response += f"📊 Пройдено: {year_stats['total_km']:.2f} км\n"
                    response += f"⭐️ Осталось: {user.goal_km - year_stats['total_km']:.2f} км\n\n"
                else:
                    response += "🎯 Цель на год не установлена\n\n"
                
                # Статистика за текущий месяц
                month_name = calendar.month_name[current_month]
                response += f"📅 <b>{month_name}</b>\n"
                response += f"├ Пробежек: {month_stats['runs_count']}\n"
                response += f"├ Дистанция: {month_stats['total_km']:.2f} км\n"
                if month_stats['runs_count'] > 0:
                    response += f"└ Средняя: {month_stats['avg_km']:.2f} км\n\n"
                else:
                    response += f"└ Средняя: 0.0 км\n\n"
                
                # Лучшие результаты
                response += f"🏆 <b>Лучшие результаты</b>\n"
                response += f"├ Пробежка: {best_stats['best_run']:.2f} км\n"
                response += f"└ Всего: {best_stats['total_runs']} пробежек\n"
                
                # Создаем клавиатуру
                markup = InlineKeyboardMarkup()
                
                # Основные действия
                markup.row(
                    InlineKeyboardButton("📝 Новая пробежка", callback_data="new_run"),
                    InlineKeyboardButton("🎯 Изменить цель", callback_data="set_goal_custom")
                )
                
                # Дополнительные действия
                markup.row(
                    InlineKeyboardButton("📊 Статистика", callback_data="show_detailed_stats"),
                    InlineKeyboardButton("✏️ История", callback_data="edit_runs")
                )
                
                # Отправляем сообщение
                if hasattr(message, 'message_id'):
                    # Если это callback query, редактируем существующее сообщение
                    self.bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        text=response,
                        reply_markup=markup,
                        parse_mode='HTML'
                    )
                else:
                    # Если это новое сообщение, отправляем новое
                    self.bot.reply_to(message, response, reply_markup=markup, parse_mode='HTML')
                    
            finally:
                db.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_profile: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.bot.reply_to(message, "❌ Произошла ошибка при получении профиля")

    def _generate_progress_bar(self, percentage, length=10):
        """Генерирует прогресс-бар заданной длины"""
        filled = int(percentage / (100 / length))
        empty = length - filled
        return '▓' * filled + '░' * empty

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Начало работы с ботом"""
    try:
        user_id = str(message.from_user.id)
        username = message.from_user.username or message.from_user.first_name
        
        user = User.get_by_id(user_id)
        if not user:
            user = User.create(user_id=user_id, username=username)
            logger.info(f"Created new user: {username} ({user_id})")
        
        welcome_message = (
            f"👋 Добро пожаловать, {username}!\n\n"
            "🎯 *RunTracker* поможет вам достигать спортивных целей:\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "*1. Записывайте пробежки*\n"
            "• Отправьте дистанцию: `5.2`\n"
            "• Добавьте описание: `5.2 Утренняя пробежка`\n"
            "• Прикрепите фото с подписью\n\n"
            "*2. Отслеживайте прогресс*\n"
            "• /stats - ваша статистика 📊\n"
            "• /history - история пробежек 📅\n"
            "• /mystats - детальный анализ 📈\n\n"
            "*3. Соревнуйтесь*\n"
            "• /top - таблица лидеров 🏆\n"
            "• /challenges - участвуйте в челленджах 🎯\n"
            "• /createteam - создайте команду 👥\n\n"
            "🔍 Используйте /help для просмотра всех команд\n"
            "⚡️ Совет: Установите годовую цель командой /setgoal"
        )
        
        bot.reply_to(message, welcome_message, parse_mode='Markdown')
        logger.info(f"Sent welcome message to user {user_id}")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        error_message = (
            "😔 Произошла ошибка при запуске\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору"
        )
        bot.reply_to(message, error_message)

@bot.message_handler(commands=['help'])
def help_handler(message):
    """Показывает список всех команд"""
    help_text = (
        "*🤖 Команды RunTracker*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*📊 Статистика и анализ*\n"
        "• /stats - основные показатели\n"
        "• /mystats - детальная статистика\n"
        "• /history - ваши пробежки\n"
        "• /top - рейтинг бегунов\n\n"
        "*🎯 Цели и достижения*\n"
        "• /setgoal `<км>` - годовая цель\n"
        "• /progress - текущий прогресс\n\n"
        "*📝 Запись пробежек*\n"
        "• Отправьте километраж: `5.2`\n"
        "• С описанием: `5.2 Парковая пробежка`\n"
        "• Фото с подписью дистанции\n\n"
        "*🏆 Челленджи*\n"
        "• /challenges - активные челленджи\n"
        "• /mychallenges - ваши челленджи\n"
        "• /joinchallenge `<ID>` - участвовать\n"
        "• /leavechallenge `<ID>` - покинуть\n\n"
        "*👥 Команды*\n"
        "• /createteam `<название>` - создать\n"
        "• /jointeam `<ID>` - присоединиться\n"
        "• /teamstats - статистика команды\n\n"
        "💡 Совет: Закрепите бота для быстрого доступа"
    )
    
    bot.reply_to(message, help_text, parse_mode='Markdown')
    logger.info(f"Sent help message to user {message.from_user.id}")

def register_message_handlers(bot):
    """Регистрирует обработчики сообщений"""
    handler = MessageHandler(bot)
    handler.register()

def register_handlers(bot):
    """Регистрирует все обработчики"""
    register_message_handlers(bot)  # Используем только один обработчик сообщений
    private_handlers.register_handlers(bot)

def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Starting bot...")
        
        # Создаем таблицы в базе данных
        Base.metadata.create_all(engine)
        logger.info("Database tables created")
        
        # Регистрируем обработчики
        register_handlers(bot)  # Регистрируем все обработчики
        register_chat_handlers(bot)
        register_challenge_handlers(bot)
        register_team_handlers(bot)
        register_stats_handlers(bot)
        register_goal_handlers(bot)
        register_chat_goal_handlers(bot)
        AdminHandler(bot).register()
        ResetHandler(bot).register()
        DonateHandler(bot).register()
        
        logger.info("Bot handlers registered")
        
        # Запускаем бота
        logger.info("Bot is running...")
        bot.infinity_polling()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
   main()