#!/bin/bash

# Активируем виртуальное окружение
source venv/bin/activate

# Применяем миграции
alembic upgrade head

# Запускаем бота
python main.py 