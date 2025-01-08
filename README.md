# Running Bot

Телеграм бот для отслеживания пробежек в чате.

## Требования
- Python 3.8+
- SQLite3
- virtualenv (опционально)

## Установка

1. Клонируйте репозиторий:
```bash
git clone [URL репозитория]
cd sl_tg_bot
```

2. Создайте и активируйте виртуальное окружение (опционально):
```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте конфигурацию:
- Скопируйте `config/config.example.py` в `config/config.py`
- Укажите ваш токен бота в `config/config.py`

5. Инициализируйте базу данных:
```bash
alembic upgrade head
```

## Запуск

Для запуска бота выполните:
```bash
python3 main.py
```

## Запуск в фоновом режиме (на сервере)

Для запуска бота в фоновом режиме используйте:
```bash
nohup python3 main.py > bot.log 2>&1 &
```

Для остановки бота:
```bash
pkill -f "python3 main.py"
```

## Обновление на сервере

1. Остановите текущий процесс бота:
```bash
pkill -f "python3 main.py"
```

2. Получите последние изменения:
```bash
git pull origin main
```

3. Обновите зависимости:
```bash
pip install -r requirements.txt
```

4. Примените миграции базы данных:
```bash
alembic upgrade head
```

5. Запустите бота снова:
```bash
nohup python3 main.py > bot.log 2>&1 &
```

## Мониторинг

Для просмотра логов:
```bash
tail -f bot.log
```