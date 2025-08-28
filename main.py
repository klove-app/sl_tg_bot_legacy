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
        
        # Проверяем наличие API ключа
        if not cfg.STABILITY_API_KEY or cfg.STABILITY_API_KEY == 'your_api_key_here':
            logger.warning("Stability AI API key not configured, skipping image generation")
            return None
        
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
            "width": 1024,  # Исправляем размеры для SDXL
            "height": 1024,
            "style_preset": "anime"
        }
        logger.info("Payload prepared")
        
        logger.info("Sending request to Stability AI")
        # Добавляем timeout для избежания зависания
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        logger.info(f"Got response with status code: {response.status_code}")
        
        if response.status_code == 401:
            logger.error("Stability AI API: Unauthorized - check API key")
            return None
        elif response.status_code == 402:
            logger.error("Stability AI API: Payment required - check account balance")
            return None
        elif response.status_code == 429:
            logger.error("Stability AI API: Rate limit exceeded")
            return None
        elif response.status_code != 200:
            logger.error(f"Stability AI API error {response.status_code}: {response.text}")
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
            "Running Club",          # Название чата
            f"{distance:.2f} km",    # Километраж на английском
            distance                 # Для позиционирования
        )
        logger.info("Watermark added")
        
        return watermarked_image
        
    except requests.exceptions.Timeout:
        logger.error("Stability AI API request timeout")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Stability AI API connection error")
        return None
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
            # Linux fonts (Railway)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf",
            # Windows fonts
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            # macOS fonts
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
        ]
        
        found_fonts = []
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    logger.info(f"Найден шрифт: {font_path}")
                    found_fonts.append(font_path)
            except Exception as e:
                logger.error(f"Ошибка при проверке шрифта {font_path}: {e}")
        
        # Пытаемся загрузить шрифты
        font_large = None
        font_medium = None
        font_brand = None
        
        if found_fonts:
            # Используем первый найденный шрифт
            font_path = found_fonts[0]
            logger.info(f"Используем шрифт: {font_path}")
            
            try:
                # Увеличиваем размеры шрифтов для лучшей читаемости
                font_large = ImageFont.truetype(font_path, 80)   # Для главного километража
                font_medium = ImageFont.truetype(font_path, 36)  # Для подписей и информации
                font_small = ImageFont.truetype(font_path, 28)   # Для мелкого текста
                logger.info("Шрифты успешно загружены")
            except Exception as e:
                logger.error(f"Ошибка при загрузке шрифтов: {e}")
        
        # Fallback на стандартный шрифт PIL
        if not font_large:
            logger.warning("Используем стандартный шрифт PIL")
            try:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
                logger.info("Стандартный шрифт загружен")
            except Exception as e:
                logger.error(f"Ошибка при загрузке стандартного шрифта: {e}")
                return None
            
        # Размеры изображения
        width, height = image.size
        
        # === СТИЛЬНЫЙ ДИЗАЙН В СТИЛЕ STRAVA/INSTAGRAM ===
        
        # Создаем градиентный фон для нижней панели (как в Strava)
        panel_height = 100  # Уменьшаем высоту панели
        gradient_overlay = Image.new('RGBA', (width, panel_height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient_overlay)
        
        # Создаем градиент от прозрачного к черному
        for y in range(panel_height):
            alpha = int((y / panel_height) * 160)  # Немного уменьшаем прозрачность
            gradient_draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))
        
        # Накладываем градиент снизу
        image.paste(gradient_overlay, (0, height - panel_height), gradient_overlay)
        
        # === ВЕРХНИЙ ЛОГОТИП (как в Strava) ===
        brand_text = "🏃‍♂️ Running Club"
        
        # Создаем стильную рамку для логотипа
        brand_bbox = draw.textbbox((0, 0), brand_text, font=font_small)
        brand_width = brand_bbox[2] - brand_bbox[0]
        brand_height = brand_bbox[3] - brand_bbox[1]
        
        # Полупрозрачная рамка с закругленными краями (имитация)
        logo_padding = 12  # Уменьшаем отступы
        logo_bg = Image.new('RGBA', (brand_width + logo_padding * 2, brand_height + logo_padding * 2), (0, 0, 0, 140))
        
        # Размещаем логотип в правом верхнем углу
        logo_x = width - brand_width - logo_padding * 2 - 15  # Ближе к краю
        logo_y = 15  # Ближе к верху
        image.paste(logo_bg, (logo_x, logo_y), logo_bg)
        draw.text((logo_x + logo_padding, logo_y + logo_padding), brand_text, font=font_small, fill='white')
        
        # === ОСНОВНАЯ ИНФОРМАЦИЯ ВНИЗУ (как в Strava) ===
        
        # Большой километраж (главная метрика)
        main_distance = distance_text
        distance_bbox = draw.textbbox((0, 0), main_distance, font=font_large)
        distance_width = distance_bbox[2] - distance_bbox[0]
        
        # Размещаем километраж по центру внизу
        distance_x = (width - distance_width) // 2
        distance_y = height - 70  # Поднимаем выше
        
        # Добавляем тень для лучшей читаемости
        shadow_offset = 2
        draw.text((distance_x + shadow_offset, distance_y + shadow_offset), main_distance, font=font_large, fill=(0, 0, 0, 150))
        draw.text((distance_x, distance_y), main_distance, font=font_large, fill='white')
        
        # Подпись "DISTANCE" под километражем
        label_text = "DISTANCE"
        label_bbox = draw.textbbox((0, 0), label_text, font=font_small)
        label_width = label_bbox[2] - label_bbox[0]
        label_x = (width - label_width) // 2
        label_y = distance_y + 40  # Ближе к километражу
        
        draw.text((label_x + 1, label_y + 1), label_text, font=font_small, fill=(0, 0, 0, 150))  # Тень
        draw.text((label_x, label_y), label_text, font=font_small, fill=(200, 200, 200))  # Серый текст
        
        # === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===
        
        # Имя пользователя и дата слева внизу
        user_info = f"@{info_text.split(' • ')[0]} • {info_text.split(' • ')[1]}"
        draw.text((16, height - 20), user_info, font=font_small, fill=(0, 0, 0, 150))  # Тень
        draw.text((15, height - 21), user_info, font=font_small, fill='white')
        
        # Мотивационная фраза справа внизу (как в Strava)
        # Используем distance_x для проверки дистанции (это правильная переменная)
        actual_distance = float(distance_text.replace(' км', '').replace(' km', ''))
        if actual_distance >= 10:
            motivation = "💪 AWESOME!"
        elif actual_distance >= 5:
            motivation = "🔥 GREAT JOB!"
        else:
            motivation = "👍 KEEP GOING!"
            
        motivation_bbox = draw.textbbox((0, 0), motivation, font=font_small)
        motivation_width = motivation_bbox[2] - motivation_bbox[0]
        motivation_x = width - motivation_width - 15
        
        draw.text((motivation_x + 1, height - 20), motivation, font=font_small, fill=(0, 0, 0, 150))  # Тень
        draw.text((motivation_x, height - 21), motivation, font=font_small, fill=(255, 165, 0))  # Оранжевый как в Strava
        
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
    
    # Удаляем webhook перед запуском polling (исправление конфликта 409)
    try:
        logger.info("Deleting webhook to avoid conflict with polling...")
        bot.delete_webhook()
        logger.info("Webhook deleted successfully")
        
        # Дополнительная пауза для завершения предыдущих соединений
        import time
        time.sleep(2)
        logger.info("Waiting for previous connections to close...")
        
    except Exception as e:
        logger.warning(f"Failed to delete webhook: {e}")
    
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
    
    # Запускаем бота с улучшенной обработкой ошибок
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"Starting bot polling (attempt {retry_count + 1}/{max_retries})...")
            bot.infinity_polling(
                timeout=20, 
                long_polling_timeout=20,
                allowed_updates=["message", "edited_message", "callback_query"],
                skip_pending=True  # Пропускаем старые сообщения при запуске
            )
            break  # Если polling запустился успешно, выходим из цикла
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Error in bot polling (attempt {retry_count}/{max_retries}): {e}")
            
            if "terminated by other getUpdates request" in str(e):
                logger.warning("Another bot instance detected. Waiting before retry...")
                import time
                time.sleep(5)  # Ждем 5 секунд перед повторной попыткой
                
                # Пытаемся снова удалить webhook
                try:
                    bot.delete_webhook()
                    time.sleep(2)
                except:
                    pass
                    
            elif retry_count >= max_retries:
                logger.error("Max retries reached. Bot startup failed.")
                logger.error(traceback.format_exc())
                raise
            else:
                logger.info(f"Retrying in 3 seconds...")
                import time
                time.sleep(3)