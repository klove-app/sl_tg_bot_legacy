# RunTracker Bot v2

Чистая версия Telegram-бота для группового учёта пробежек. Рейтинги и статистика
изолированы по `chat_id`; данные разных групп не смешиваются.

## Команды

- `/run 5.2` — записать 5,2 км
- `/run 10 утренний парк` — записать пробежку с заметкой
- `/top` — рейтинг группы за неделю, месяц, год или всё время
- `/me` — личная статистика в этой группе
- `/undo` — удалить свою последнюю запись после подтверждения
- `/help` — помощь

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m app.main
```

Нужны новый токен от `@BotFather` и PostgreSQL `DATABASE_URL`. Не используйте
токены, которые когда-либо попадали в GitHub, чат или скриншоты.

## Тесты

```bash
pytest
ruff check .
```

## Railway

Создайте новый service из этой ветки и укажите Root Directory `/v2`. Переменные:

- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL` (ссылка на существующий Railway Postgres)
- `BOT_TIMEZONE`, например `Europe/Moscow`
- `MAX_DISTANCE_KM`, по умолчанию `100`
- `ALLOWED_CHAT_IDS` — необязательный allow-list через запятую

Для staging используйте отдельного Telegram-бота. Не запускайте legacy и v2 с
одним токеном одновременно.

## Перенос legacy-данных

Сначала только просмотр:

```bash
python -m scripts.import_legacy
```

После проверки количества строк:

```bash
python -m scripts.import_legacy --apply
```

Можно ограничить импорт одной группой через `--chat-id`. Импортируются только
строки с `chat_id`; повторный запуск безопасен.

Подробнее: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
