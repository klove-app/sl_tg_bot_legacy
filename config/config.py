TOKEN = '6329273445:AAEsQKLCr2BjNvjjFZhdWs224AoAN7UXqno'
ADMIN_IDS = ['1431390352']

# Настройки базы данных
import os
DATABASE_NAME = 'running_bot.db'  # Для локальной разработки
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DATABASE_NAME}')  # Используем Railway URL в продакшене

# Настройки Stability AI
STABILITY_API_HOST = 'https://api.stability.ai'
STABILITY_API_KEY = 'sk-R4NRtaGn4CoNOgtOlFRwJ1I1W0PjjpMFOI8gcC7lLwY5pLn4'
STABLE_DIFFUSION_ENGINE_ID = 'stable-diffusion-xl-1024-v1-0' 