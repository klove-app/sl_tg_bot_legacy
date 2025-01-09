from bot_instance import bot
from handlers.user_handlers import DonateHandler

def register_handlers():
    DonateHandler(bot).register()

if __name__ == '__main__':
    register_handlers()
    bot.infinity_polling() 