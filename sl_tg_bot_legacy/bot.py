from telebot import TeleBot
from config.config import BOT_TOKEN
from config.context import get_context, update_context
from handlers.private_handlers import register_private_handlers
from handlers.chat_handlers import register_chat_handlers
from handlers.stats_handlers import register_handlers
from database.base import init_db
from database.logger import logger

def main():
    """Основная функция запуска бота"""
    logger.info("Starting bot initialization")
    
    # Загружаем контекст
    logger.info("Loading context")
    context = get_context()
    logger.info(f"Bot context loaded: {context['project_context']['name']}")
    
    # Инициализируем базу данных
    logger.info("Initializing database")
    init_db()
    
    # Создаем экземпляр бота
    logger.info("Creating bot instance")
    bot = TeleBot(BOT_TOKEN)
    
    # Обновляем контекст с информацией о боте
    update_context('runtime.bot_instance', {
        'username': bot.get_me().username,
        'started_at': __import__('datetime').datetime.now().isoformat()
    })
    
    # Регистрируем обработчики
    logger.info("Registering handlers")
    register_private_handlers(bot)
    register_chat_handlers(bot)
    register_handlers(bot)
    logger.info("Handlers registered successfully")
    
    # Запускаем бота
    logger.info("Starting bot polling")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Error in bot polling: {e}")
        raise

if __name__ == "__main__":
    main() 