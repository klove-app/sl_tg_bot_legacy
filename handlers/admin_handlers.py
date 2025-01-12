from bot_instance import bot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
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
        
        self.bot.register_callback_query_handler(
            self.handle_text_report,
            func=lambda call: call.data == "text_report"
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

            # Создаем клавиатуру с кнопкой WebApp
            keyboard = InlineKeyboardMarkup()
            webapp_btn = InlineKeyboardButton(
                text="📊 Открыть интерактивный отчет",
                web_app=WebAppInfo(url="https://your-webapp-url.com")
            )
            text_btn = InlineKeyboardButton(
                text="📝 Текстовый отчет",
                callback_data="text_report"
            )
            keyboard.add(webapp_btn)
            keyboard.add(text_btn)

            self.bot.reply_to(
                message,
                "Выберите формат отчета:",
                reply_markup=keyboard
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_report: {e}")
            self.bot.reply_to(message, "❌ Произошла ошибка при генерации отчета")

    def handle_text_report(self, call):
        """Отправляет текстовый отчет"""
        try:
            user_id = str(call.from_user.id)
            
            # Проверяем, что команду вызвал администратор
            if user_id not in ADMIN_IDS:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ У вас нет прав для выполнения этой команды"
                )
                return

            # Получаем текущий год и месяц
            current_year = datetime.now().year
            current_month = datetime.now().month
            
            # Формируем HTML отчет
            report = self.generate_report(current_year, current_month)
            
            # Отправляем отчет
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=report,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in handle_text_report: {e}")
            self.bot.answer_callback_query(
                call.id,
                "❌ Произошла ошибка при генерации отчета"
            )

    def generate_report(self, year: int, month: int) -> str:
        """Генерирует подробный HTML-отчет"""
        def progress_bar(value, max_value, width=20):
            """Создает графический прогресс-бар с цветовыми акцентами"""
            if max_value <= 0:
                return "⬜️" * width
            filled = int(width * value / max_value)
            percent = value / max_value * 100
            
            if percent >= 100:
                filled_char = "🟦"  # синий для перевыполнения
            elif percent >= 75:
                filled_char = "🟩"  # зеленый для хорошего прогресса
            elif percent >= 50:
                filled_char = "🟨"  # желтый для среднего прогресса
            else:
                filled_char = "🟧"  # оранжевый для начального прогресса
            
            return filled_char * filled + "⬜️" * (width - filled)

        report = (
            f"<b>📊 СВОДНЫЙ ОТЧЕТ ЗА {year} ГОД</b>\n"
            f"<pre>━━━━━━━━━━━━━━━━━━━━━━</pre>\n\n"
        )
        
        # 1. Общая статистика
        total_stats = RunningLog.get_total_stats(year)
        total_km = float(total_stats['total_km'])
        avg_km = float(total_stats['avg_km'])
        
        report += (
            "<b>🌟 ОБЩАЯ СТАТИСТИКА</b>\n"
            "<pre>┌────────────────────────────────────┐\n"
            f"│ 🏃 Пробежек:     {total_stats['runs_count']:5d}           │\n"
            f"│ 📏 Всего:     {total_km:7.2f}км           │\n"
            f"│ 👥 Бегунов:      {total_stats['users_count']:5d}           │\n"
        )
        if total_stats['runs_count'] > 0:
            report += f"│ ⚡️ Средняя:    {avg_km:7.2f}км           │\n"
        report += "└────────────────────────────────────┘</pre>\n\n"
        
        # 2. Статистика по месяцам
        report += "<b>📅 СТАТИСТИКА ПО МЕСЯЦАМ</b>\n<pre>"
        report += "┌────────────────────────────────────┐\n"
        report += "│ Месяц  Проб.  Дист.    Прогресс   │\n"
        report += "├────────────────────────────────────┤\n"
        
        max_km = 0
        month_data = []
        for m in range(1, month + 1):
            stats = RunningLog.get_total_stats(year, m)
            km = float(stats['total_km'])
            max_km = max(max_km, km)
            month_data.append((m, km, stats['runs_count']))

        for m, km, runs in month_data:
            bar = progress_bar(km, max_km, 10)
            report += f"│ {m:02d}.{year}  {runs:4d}  {km:6.2f}км  {bar}   │\n"
            if m < len(month_data):
                report += "├────────────────────────────────────┤\n"
        report += "└────────────────────────────────────┘</pre>\n\n"
        
        # 3. Топ бегунов
        top_runners = RunningLog.get_top_runners(year=year, limit=10)
        if top_runners:
            report += "<b>🏆 ТОП-10 БЕГУНОВ</b>\n<pre>"
            report += "┌────────────────────────────────────┐\n"
            report += "│ Место  Бегун   Дист.    Прогресс  │\n"
            report += "├────────────────────────────────────┤\n"
            
            medals = ["🥇", "🥈", "🥉"]
            for i, runner in enumerate(top_runners, 1):
                user = User.get_by_id(runner['user_id'])
                username = user.username if user else "Unknown"
                runner_km = float(runner['total_km'])
                percent = (runner_km / total_km * 100) if total_km > 0 else 0
                bar = progress_bar(runner_km, total_km, 10)
                
                medal = medals[i-1] if i <= 3 else " "
                report += f"│{medal}{i:2d}.  {username[:8]:<8} {runner_km:5.2f}км  {bar}   │\n"
                if i < len(top_runners):
                    report += "├────────────────────────────────────┤\n"
            report += "└────────────────────────────────────┘</pre>\n\n"
        
        # 4. Активные челленджи
        challenges = Challenge.get_active_challenges()
        if challenges:
            report += "<b>🎯 АКТИВНЫЕ ЧЕЛЛЕНДЖИ</b>\n<pre>"
            report += "┌────────────────────────────────────┐\n"
            report += "│ Название   Цель     Прогресс       │\n"
            report += "├────────────────────────────────────┤\n"
            
            for challenge in challenges:
                total_km = float(challenge.get_total_progress() or 0)
                goal_km = float(challenge.goal_km or 0)
                progress = (total_km / goal_km * 100) if goal_km > 0 else 0
                bar = progress_bar(total_km, goal_km, 10)
                
                title = challenge.title[:10] if challenge.title else "Без имени"
                if goal_km == 0:
                    report += f"│ {title:<10} {goal_km:4.0f}км                      │\n"
                else:
                    report += f"│ {title:<10} {goal_km:4.0f}км  {bar} {progress:3.0f}%   │\n"
                if challenge != challenges[-1]:
                    report += "├────────────────────────────────────┤\n"
            report += "└────────────────────────────────────┘</pre>\n\n"
        
        # 5. Статистика по чатам
        chat_stats = RunningLog.get_chat_stats_all(year)
        if chat_stats:
            report += "<b>💬 СТАТИСТИКА ПО ЧАТАМ</b>\n<pre>"
            report += "┌────────────────────────────────────┐\n"
            report += "│  Чат    Проб.  Дист.    Прогресс  │\n"
            report += "├────────────────────────────────────┤\n"
            
            max_chat_km = max(float(chat['total_km']) for chat in chat_stats)
            for chat in chat_stats:
                chat_id_short = str(chat['chat_id'])[-6:]
                chat_km = float(chat['total_km'])
                percent = (chat_km / max_chat_km * 100)
                bar = progress_bar(chat_km, max_chat_km, 10)
                
                if chat_km == 0:
                    report += f"│ {chat_id_short:<6} {chat['runs_count']:4d}  {chat_km:6.2f}км             │\n"
                else:
                    report += f"│ {chat_id_short:<6} {chat['runs_count']:4d}  {chat_km:6.2f}км  {bar}   │\n"
                if chat != chat_stats[-1]:
                    report += "├────────────────────────────────────┤\n"
            report += "└────────────────────────────────────┘</pre>\n"
        
        return report

def register_handlers(bot):
    """Регистрирует обработчики администратора"""
    handler = AdminHandler(bot)
    handler.register() 