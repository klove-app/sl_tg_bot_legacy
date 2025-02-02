import logging
import os
from datetime import datetime

# Создаем директорию для логов, если её нет
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Создаем имя файла с текущей датой
log_file = os.path.join(log_dir, f'bot_{datetime.now().strftime("%Y%m%d")}.log')

# Настраиваем логгер
logger = logging.getLogger('running_bot')
logger.setLevel(logging.DEBUG)

# Создаем форматтер
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Создаем обработчик для вывода в файл
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Добавляем обработчики к логгеру
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Добавляем информацию о запуске
logger.info("="*50)
logger.info("Logger initialized") 