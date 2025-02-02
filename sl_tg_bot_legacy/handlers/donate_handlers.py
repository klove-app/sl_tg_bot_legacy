from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.base_handler import BaseHandler

class DonateHandler(BaseHandler):
    def register(self):
        self.bot.register_message_handler(
            self.handle_donate,
            commands=['donate', 'support']
        )

    def handle_donate(self, message):
        """Показывает меню с вариантами донатов"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # Варианты донатов
        donations = [
            ("☕️ Кофе (100₽)", "https://yoomoney.ru/to/4100118963809958/100"),
            ("🎯 Поддержка (300₽)", "https://yoomoney.ru/to/4100118963809958/300"),
            ("❤️ Спонсор (500₽)", "https://yoomoney.ru/to/4100118963809958/500")
        ]
        
        for title, url in donations:
            keyboard.add(InlineKeyboardButton(text=title, url=url))
            
        keyboard.add(InlineKeyboardButton(
            "💎 Произвольная сумма",
            url="https://yoomoney.ru/to/4100118963809958"
        ))
        
        self.bot.reply_to(
            message,
            "🤝 Спасибо за желание поддержать проект!\n\n"
            "💡 Выберите сумму доната или укажите свою:",
            reply_markup=keyboard
        ) 