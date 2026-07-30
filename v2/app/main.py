from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.config import get_settings
from app.db import create_database, create_schema
from app.handlers import router
from app.middleware import DatabaseSessionMiddleware


async def run_bot() -> None:
    settings = get_settings()
    if settings.telegram_bot_token is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to start the bot")
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("runtracker")

    database = create_database(settings.database_url)
    await create_schema(database.engine)

    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    middleware = DatabaseSessionMiddleware(database.sessions)
    router.message.outer_middleware(middleware)
    router.callback_query.outer_middleware(middleware)
    dispatcher.include_router(router)

    try:
        me = await bot.get_me()
        await bot.set_my_commands(
            [
                BotCommand(command="run", description="Записать пробежку: /run 5.2"),
                BotCommand(command="top", description="Рейтинг группы"),
                BotCommand(command="me", description="Моя статистика"),
                BotCommand(command="undo", description="Удалить последнюю запись"),
                BotCommand(command="help", description="Помощь"),
            ]
        )
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Starting @%s with long polling", me.username)
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
            settings=settings,
            bot_username=me.username or "",
        )
    finally:
        await bot.session.close()
        await database.engine.dispose()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
