from bot_instance import bot
from database.logger import logger

@bot.message_handler(commands=['help'])
def show_help(message):
    """Показывает список всех доступных команд"""
    help_text = (
        "🏃‍♂️ <b>Бот для учета пробежек</b>\n\n"
        
        "📝 <b>Регистрация пробежек:</b>\n"
        "├ Просто отправьте боту сообщение с\n"
        "├ количеством пройденных километров\n"
        "└ Например: 5.2 или 10\n\n"
        
        "📊 <b>Статистика:</b>\n"
        "├ /stats - Личная статистика\n"
        "└ /top - Рейтинг бегунов\n\n"
        
        "🎯 <b>Личные цели:</b>\n"
        "├ /setgoal - Установить личную цель\n"
        "└ /checkgoal - Проверить установленные цели\n\n"
        
        "👥 <b>Групповые цели (только для админов):</b>\n"
        "├ /chatgoal - Статистика общей цели\n"
        "├ /setchatgoal - Установить цель для чата\n"
        "└ /updatechatgoal - Изменить цель чата\n\n"
        
        "ℹ️ <b>Дополнительно:</b>\n"
        "├ /start - Начать работу с ботом\n"
        "└ /help - Показать это сообщение\n\n"
        
        "💡 <b>Подсказки:</b>\n"
        "├ Бот принимает числа с точкой или запятой, так же можно добавить заметку в свободном виде\n"
        "├ Статистика обновляется автоматически\n"
        "└ Общая цель считается для всего чата"
    )
    
    try:
        bot.reply_to(message, help_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error in show_help: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при отображении помощи") 