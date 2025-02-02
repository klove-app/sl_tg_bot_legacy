from datetime import datetime
import traceback
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models.challenge import Challenge
from database.models.user import User
from database.models.running_log import RunningLog
from utils.formatters import round_km
from database.base import get_db
from database.logger import logger
from sqlalchemy import func, extract

def register_chat_handlers(bot):
    """Регистрация обработчиков чата"""
    logger.info("Starting chat handlers registration...")

    def show_top(message):
        """Показывает топ бегунов в чате"""
        logger.info(f"Processing /top command. Message: {message.text}")
        try:
            year = datetime.now().year
            
            logger.debug(f"Processing /top for year {year}")
            
            db = next(get_db())
            
            # Получаем общую статистику
            total_stats = db.query(
                func.count(func.distinct(RunningLog.user_id)).label('total_users'),
                func.count().label('total_runs'),
                func.sum(RunningLog.km).label('total_distance')
            ).filter(
                extract('year', RunningLog.date_added) == year
            ).first()
            
            if not total_stats or not total_stats.total_distance:
                logger.debug("No running data found")
                bot.reply_to(message, "📊 Пока нет данных о пробежках в этом году")
                return

            total_users = total_stats.total_users
            total_runs = total_stats.total_runs
            total_distance = float(total_stats.total_distance)
            
            # Получаем статистику по пользователям
            results = db.query(
                User.username,
                func.count().label('runs_count'),
                func.sum(RunningLog.km).label('total_km'),
                func.avg(RunningLog.km).label('avg_km'),
                func.max(RunningLog.km).label('best_run')
            ).join(
                User, RunningLog.user_id == User.user_id
            ).filter(
                extract('year', RunningLog.date_added) == year
            ).group_by(
                RunningLog.user_id, User.username
            ).order_by(
                func.sum(RunningLog.km).desc()
            ).limit(10).all()

            response = (
                f"📊 Статистика бегунов {year}\n"
                f"👥 {total_users} участников • 🏃‍♂️ {total_runs} пробежек • 📏 {total_distance:.2f} км\n\n"
                f"🏆 Рейтинг:\n"
            )
            
            for i, result in enumerate(results, 1):
                username = result.username
                runs_count = result.runs_count
                total_km = float(result.total_km)
                avg_km = float(result.avg_km)
                best_run = float(result.best_run)
                
                # Определяем медаль и процент от общей дистанции
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                total_percent = (total_km / total_distance * 100)
                
                response += (
                    f"\n{medal} @{username} • {total_km:.2f} км ({total_percent:.1f}%)\n"
                    f"   {runs_count} пробежек • ⌀{avg_km:.2f} км • 🔥{best_run:.2f} км\n"
                )

            bot.reply_to(message, response, parse_mode='HTML')
            logger.info("Top runners shown")
            
        except Exception as e:
            logger.error(f"Error in show_top: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            bot.reply_to(message, "❌ Произошла ошибка при получении топа")

    # Регистрируем обработчики
    bot.message_handler(commands=['top'])(show_top)
    logger.info("Chat handlers registered successfully")