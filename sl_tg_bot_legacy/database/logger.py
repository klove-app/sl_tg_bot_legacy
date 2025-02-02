import logging
import sys

# Настраиваем корневой логгер
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/running_bot.log')
    ]
)

# Настраиваем логгер для нашего приложения
logger = logging.getLogger('running_bot')
logger.setLevel(logging.DEBUG)

# Создаем обработчик для вывода в stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Создаем обработчик для файла
file_handler = logging.FileHandler('/tmp/running_bot.log')
file_handler.setLevel(logging.DEBUG)

# Создаем форматтер с дополнительной информацией
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Удаляем существующие обработчики
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Добавляем обработчики к логгеру
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Включаем логирование SQL-запросов
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.DEBUG)
sqlalchemy_logger.addHandler(console_handler)
sqlalchemy_logger.addHandler(file_handler)

# Проверяем, что логгер работает
logger.debug("Logger initialized with DEBUG level")
logger.info("Logger initialized with handlers: stdout and file") 