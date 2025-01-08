from telebot.types import Message
from database.models.running_log import RunningLog
from handlers.base_handler import BaseHandler
from datetime import datetime, date
from config.config import ADMIN_IDS
from database.db import get_connection

class AdminHandler(BaseHandler):
    def register(self):
        """Регистрирует обработчики администратора"""
        self.logger.info("Registering admin handlers")
        
        self.bot.register_message_handler(
            self.handle_delete_test_data,
            commands=['delete_test_data'],
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

def register_handlers(bot):
    """Регистрирует обработчики администратора"""
    handler = AdminHandler(bot)
    handler.register() 