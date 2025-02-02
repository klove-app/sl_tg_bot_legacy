import logging

# Настраиваем корневой логгер
logging.basicConfig(level=logging.DEBUG)

# Настраиваем логгер для нашего приложения
logger = logging.getLogger('running_bot')
logger.setLevel(logging.DEBUG)

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Создаем форматтер с дополнительной информацией
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
console_handler.setFormatter(formatter)

# Удаляем существующие обработчики
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Добавляем обработчик к логгеру
logger.addHandler(console_handler)

# Включаем логирование SQL-запросов
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG) 