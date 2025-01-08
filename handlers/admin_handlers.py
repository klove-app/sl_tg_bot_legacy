from telebot.types import Message
from database.models.running_log import RunningLog
from handlers.base_handler import BaseHandler
from datetime import datetime, date
from config.config import ADMIN_IDS
from database.db import get_connection
from database.models.user import User
from database.models.challenge import Challenge

class AdminHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики администратора"""
        self.logger.info("Registering admin handlers")
        
        self.bot.register_message_handler(
            self.handle_delete_test_data,
            commands=['delete_test_data'],
            func=lambda message: str(message.from_user.id) in ADMIN_IDS
        )
        
        self.bot.register_message_handler(
            self.handle_report,
            commands=['report'],
            func=lambda message: str(message.from_user.id) in ADMIN_IDS
        )
        
        self.logger.info("Admin handlers registered successfully")
        
    def handle_delete_test_data(self, message: Message):
        """Удаляет тестовые данные за 7-8 января 2025"""
        try:
            user_id = str(message.from_user.id)
            
            # Проверяем, что команду вызвал администратор
            if user_id not in ADMIN_IDS:
                self.bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды")
                return
            
            # Проверяем записи за 7-8 января 2025
            start_date = date(2025, 1, 7)
            end_date = date(2025, 1, 8)
            
            # Сначала получаем список записей
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """SELECT user_id, km, date_added 
                       FROM running_log 
                       WHERE date_added BETWEEN ? AND ?""",
                    (start_date.isoformat(), end_date.isoformat())
                )
                records = cursor.fetchall()
                
                if not records:
                    self.bot.reply_to(message, "❌ Записей за 7-8 января 2025 не найдено")
                    return
                
                # Формируем сообщение с найденными записями
                preview = "Найдены следующие записи для удаления:\n\n"
                for user_id, km, date_added in records:
                    preview += f"👤 Пользователь: {user_id}\n"
                    preview += f"🏃‍♂️ Дистанция: {km} км\n"
                    preview += f"📅 Дата: {date_added}\n\n"
                
                # Отправляем предварительный просмотр
                self.bot.reply_to(message, preview)
                
                # Удаляем записи
                deleted_count = RunningLog.delete_entries_by_date_range(start_date, end_date)
                
                self.bot.reply_to(
                    message,
                    f"✅ Удалено {deleted_count} тестовых записей за период 7-8 января 2025"
                )
            finally:
                cursor.close()
                conn.close()
            
        except Exception as e:
            self.logger.error(f"Error in handle_delete_test_data: {e}")
            self.bot.reply_to(message, "❌ Произошла ошибка при удалении тестовых данных")

    def handle_report(self, message: Message):
        """Генерирует и отправляет подробный отчет"""
        try:
            user_id = str(message.from_user.id)
            
            # Проверяем, что команду вызвал администратор
            if user_id not in ADMIN_IDS:
                self.bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды")
                return

            # Получаем текущий год и месяц
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            # Формируем HTML отчет
            report = self.generate_report(current_year, current_month)
            
            # Отправляем отчет
            self.bot.reply_to(
                message,
                report,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_report: {e}")
            self.bot.reply_to(message, "❌ Произошла ошибка при генерации отчета")

    def generate_report(self, year: int, month: int) -> str:
        """Генерирует подробный HTML-отчет"""
        report = f"<b>📊 Сводный отчет за {year} год</b>\n\n"
        
        # 1. Общая статистика
        total_stats = RunningLog.get_total_stats(year)
        report += "<b>🌟 Общая статистика</b>\n"
        report += f"• Всего пробежек: {total_stats['runs_count']}\n"
        report += f"• Общая дистанция: {total_stats['total_km']:.2f} км\n"
        report += f"• Активных пользователей: {total_stats['users_count']}\n"
        if total_stats['runs_count'] > 0:
            report += f"• Средняя дистанция: {total_stats['avg_km']:.2f} км\n"
        report += "\n"
        
        # 2. Статистика по месяцам
        report += f"<b>📅 Статистика по месяцам {year} года</b>\n"
        for m in range(1, month + 1):
            month_stats = RunningLog.get_total_stats(year, m)
            report += f"\n<b>{m:02d}.{year}</b>\n"
            report += f"• Пробежек: {month_stats['runs_count']}\n"
            report += f"• Дистанция: {month_stats['total_km']:.2f} км\n"
            report += f"• Участников: {month_stats['users_count']}\n"
        report += "\n"
        
        # 3. Топ пользователей
        top_runners = RunningLog.get_top_runners(year=year, limit=10)
        report += "<b>🏆 Топ-10 пользователей</b>\n\n"
        for i, runner in enumerate(top_runners, 1):
            user = User.get_by_id(runner['user_id'])
            username = user.username if user else "Unknown"
            report += f"{i}. {username}\n"
            report += f"• Дистанция: {runner['total_km']:.2f} км\n"
            report += f"• Пробежек: {runner['runs_count']}\n"
            report += f"• Средняя: {runner['avg_km']:.2f} км\n"
            report += f"• Лучшая: {runner['best_run']:.2f} км\n\n"
        
        # 4. Активные челленджи
        challenges = Challenge.get_active_challenges()
        report += "<b>🎯 Активные челленджи</b>\n\n"
        for challenge in challenges:
            total_km = challenge.get_total_progress()
            participants_count = challenge.get_participants_count()
            progress = (total_km / challenge.goal_km * 100) if challenge.goal_km and challenge.goal_km > 0 else 0
            
            report += f"<b>{challenge.title}</b>\n"
            report += f"• Цель: {challenge.goal_km:.2f} км\n"
            report += f"• Прогресс: {total_km:.2f} км ({progress:.2f}%)\n"
            report += f"• Участников: {participants_count}\n\n"
        
        # 5. Статистика по чатам
        report += "<b>💬 Статистика по чатам</b>\n\n"
        chat_stats = RunningLog.get_chat_stats_all(year)
        for chat in chat_stats:
            report += f"<b>Чат: {chat['chat_id']}</b>\n"
            report += f"• Пробежек: {chat['runs_count']}\n"
            report += f"• Дистанция: {chat['total_km']:.2f} км\n"
            report += f"• Участников: {chat['users_count']}\n\n"
        
        return report

def register_handlers(bot):
    """Регистрирует обработчики администратора"""
    handler = AdminHandler(bot)
    handler.register() 