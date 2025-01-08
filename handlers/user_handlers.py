from bot_instance import bot
from telebot import types
from database.logger import logger
from database.models.user import User
from database.models.challenge import Challenge
from datetime import datetime

# Словарь для хранения временных данных пользователей
user_data = {}

def create_period_keyboard():
    """Создает клавиатуру для выбора периода"""
    keyboard = types.InlineKeyboardMarkup()
    current_year = datetime.now().year
    
    # Кнопки для годов
    keyboard.row(
        types.InlineKeyboardButton(f"{current_year} год", callback_data=f"goal_year_{current_year}"),
        types.InlineKeyboardButton(f"{current_year + 1} год", callback_data=f"goal_year_{current_year + 1}")
    )
    
    # Кнопки для кварталов текущего года
    current_quarter = (datetime.now().month - 1) // 3 + 1
    row = []
    for q in range(current_quarter, 5):
        row.append(types.InlineKeyboardButton(
            f"{q} квартал {current_year}",
            callback_data=f"goal_quarter_{current_year}_{q}"
        ))
        if len(row) == 2:
            keyboard.row(*row)
            row = []
    if row:
        keyboard.row(*row)
    
    return keyboard

@bot.message_handler(commands=['setgoal'])
def set_goal(message):
    """Управление личной целью"""
    try:
        user_id = str(message.from_user.id)
        
        # Получаем все цели пользователя
        user_goals = Challenge.get_all_user_challenges(user_id)
        print(f">>> Found goals: {user_goals}")
        
        if user_goals:
            # Формируем сообщение со списком целей
            goals_text = "🎯 Ваши установленные цели:\n\n"
            for goal in user_goals:
                year = goal.start_date[:4]
                total_km = goal.get_year_progress()
                progress = (total_km / goal.goal_km * 100) if goal.goal_km > 0 else 0
                goals_text += (
                    f"📅 {year} год:\n"
                    f"Цель: {goal.goal_km:.1f} км\n"
                    f"Прогресс: {total_km:.1f} км ({progress:.1f}%)\n\n"
                )
            
            # Создаем клавиатуру только с кнопками изменения и отмены
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add("✏️ Изменить цель", "❌ Отмена")
            goals_text += "Выберите действие:"
            
        else:
            goals_text = "🎯 У вас пока нет установленных целей.\n\nВыберите год для установки цели:"
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            current_year = datetime.now().year
            markup.add(
                f"📅 Цель на {current_year}",
                f"📅 Цель на {current_year + 1}"
            )
        
        bot.reply_to(message, goals_text, reply_markup=markup)
        bot.register_next_step_handler(message, process_goal_action)
        
    except Exception as e:
        print(f">>> ERROR in set_goal: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка")

def process_goal_action(message):
    """Обрабатывает выбор действия с целями"""
    try:
        if message.text == "❌ Отмена":
            bot.reply_to(
                message, 
                "Операция отменена",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
            
        if message.text == "✏️ Изменить цель":
            bot.reply_to(
                message,
                "Укажите новое значение цели в километрах:",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(message, process_goal_update)
            return
            
        # Если выбран год для новой цели
        if message.text.startswith("📅 Цель на"):
            process_goal_year(message)
            
    except Exception as e:
        print(f">>> ERROR in process_goal_action: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка")

def process_goal_update(message):
    """Обрабатывает изменение существующей цели"""
    try:
        user_id = str(message.from_user.id)
        year = datetime.now().year
        
        try:
            new_goal_km = float(message.text.replace(',', '.'))
            if new_goal_km <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "❌ Пожалуйста, введите положительное число километров")
            return
            
        # Получаем текущую цель
        current_goal = Challenge.get_user_challenge(user_id, year)
        if current_goal:
            # Обновляем значение цели
            current_goal.goal_km = new_goal_km
            current_goal.save()
            
            # Получаем актуальный прогресс
            total_km = current_goal.get_year_progress()
            progress = (total_km / new_goal_km * 100) if new_goal_km > 0 else 0
            
            bot.reply_to(
                message,
                f"✅ Цель обновлена!\n\n"
                f"📅 Год: {year}\n"
                f"🎯 Новая цель: {new_goal_km:.1f} км\n"
                f"👣 Текущий прогресс: {total_km:.1f} км\n"
                f"📈 Выполнено: {progress:.1f}%",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.reply_to(message, "❌ Не удалось найти текущую цель")
            
    except Exception as e:
        print(f">>> ERROR in process_goal_update: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка при обновлении цели")

def process_goal_year(message):
    """Обрабатывает выбор года для цели"""
    try:
        print(f"\n>>> Processing goal year: {message.text}")
        if "Цель на" not in message.text:
            bot.reply_to(message, "❌ Пожалуйста, выберите год из предложенных вариантов")
            return
            
        year = message.text.split()[-1]  # Получаем год из текста кнопки
        user_id = str(message.from_user.id)
        print(f">>> Selected year: {year} for user: {user_id}")
        
        # Сохраняем год во временные данные
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['setting_goal_for'] = {'year': year}
        print(f">>> Saved year data: {user_data[user_id]}")
        
        bot.reply_to(
            message,
            f"Укажите цель в километрах для {year} года:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(message, process_goal_km)
        
    except Exception as e:
        print(f">>> ERROR in process_goal_year: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка")

@bot.callback_query_handler(func=lambda call: call.data.startswith('goal_'))
def handle_goal_selection(call):
    try:
        # Разбираем данные из callback
        parts = call.data.split('_')
        goal_type = parts[1]  # year или quarter
        year = int(parts[2])
        quarter = int(parts[3]) if goal_type == 'quarter' else None
        
        # Сохраняем выбранный период во временное хранилище
        user_id = str(call.from_user.id)
        user_data[user_id] = {
            'setting_goal_for': {
                'type': goal_type,
                'year': year,
                'quarter': quarter
            }
        }
        
        # Запрашиваем количество километров
        period_text = f"{'весь' if goal_type == 'year' else str(quarter) + '-й квартал'} {year} года"
        bot.edit_message_text(
            f"🎯 Укажите цель в километрах на {period_text}:",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Регистрируем следующий шаг
        bot.register_next_step_handler(call.message, process_goal_km)
        
    except Exception as e:
        logger.error(f"Error in handle_goal_selection: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка. Попробуйте снова.")

def process_goal_km(message):
    """Обрабатывает ввод километража для цели"""
    try:
        print(f"\n>>> Processing goal km: {message.text}")
        user_id = str(message.from_user.id)
        
        # Проверяем, что у нас есть сохраненный год
        if user_id not in user_data or 'setting_goal_for' not in user_data[user_id]:
            print(">>> No year data found")
            bot.reply_to(message, "❌ Произошла ошибка. Попробуйте заново через /setgoal")
            return
            
        year = user_data[user_id]['setting_goal_for']['year']
        print(f">>> Setting goal for year: {year}")
        
        try:
            goal_km = float(message.text.replace(',', '.'))
            if goal_km <= 0:
                raise ValueError
            print(f">>> Goal km value: {goal_km}")
        except ValueError:
            bot.reply_to(message, "❌ Пожалуйста, введите положительное число километров")
            return
            
        # Создаем новый челлендж
        challenge = Challenge(
            title=f"Личная цель на {year} год",
            goal_km=goal_km,
            start_date=f"{year}-01-01",
            end_date=f"{year}-12-31",
            chat_id=str(message.chat.id),
            is_system=True,
            user_id=user_id  # Добавляем user_id для связи
        )
        
        print(f">>> Created challenge object: {challenge.__dict__}")
        challenge.save()
        print(">>> Challenge saved")
        
        # Очищаем временные данные
        del user_data[user_id]['setting_goal_for']
        
        bot.reply_to(
            message,
            f"✅ Цель установлена!\n\n"
            f"📅 Год: {year}\n"
            f"🎯 Цель: {goal_km:.1f} км",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
    except Exception as e:
        print(f">>> ERROR in process_goal_km: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка при установке цели")

@bot.message_handler(commands=['checkgoal'])
def check_goal(message):
    """Показывает текущие цели пользователя"""
    try:
        user_id = str(message.from_user.id)
        user = User.get_by_id(user_id)
        
        if not user:
            bot.reply_to(message, "❌ Сначала нужно зарегистрироваться. Используйте команду /start")
            return
            
        year = datetime.now().year
        challenge = Challenge.get_user_challenge(user_id, year)
        
        if challenge:
            bot.reply_to(
                message,
                f"🎯 Ваша цель на {year} год: {challenge.goal_km} км\n"
                f"📊 Текущий прогресс: {user.get_yearly_progress(year):.1f} км"
            )
        else:
            bot.reply_to(
                message,
                f"❌ У вас пока не установлена цель на {year} год.\n"
                "Используйте команду /setgoal чтобы установить цель."
            )
            
    except Exception as e:
        logger.error(f"Error in check_goal: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при проверке цели")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показывает статистику пользователя"""
    try:
        user_id = str(message.from_user.id)
        user = User.get_by_id(user_id)
        
        if not user:
            bot.reply_to(message, "❌ Сначала нужно зарегистрироваться. Используйте команду /start")
            return
            
        year = datetime.now().year
        month = datetime.now().month
        
        # Получаем статистику
        yearly_stats = user.get_yearly_stats(year)
        monthly_stats = user.get_monthly_stats(year, month)
        best_stats = user.get_best_stats()
        recent_runs = user.get_recent_runs(limit=5)
        challenge = Challenge.get_user_challenge(user_id, year)
        
        # Формируем прогресс-бар
        if challenge and challenge.goal_km and challenge.goal_km > 0:
            progress = (yearly_stats['total_km'] / challenge.goal_km * 100)
        else:
            progress = 0
        progress_bar = "█" * int(progress / 5) + "▒" * (20 - int(progress / 5))
        
        stats_text = (
            f"📊 Статистика бега для {user.username}\n\n"
            
            f"🎯 Годовая цель: {challenge.goal_km if challenge and challenge.goal_km else 0} км\n"
            f"📈 Прогресс: {progress:.1f}%\n"
            f"{progress_bar}\n\n"
            
            f"📅 {year} год:\n"
            f"├ Пробежек: {yearly_stats['runs_count']}\n"
            f"├ Дистанция: {yearly_stats['total_km']:.1f} км\n"
            f"└ Средняя: {yearly_stats['avg_km']:.1f} км\n\n"
            
            f"📆 Текущий месяц:\n"
            f"├ Пробежек: {monthly_stats['runs_count']}\n"
            f"├ Дистанция: {monthly_stats['total_km']:.1f} км\n"
            f"└ Средняя: {monthly_stats['avg_km']:.1f} км\n\n"
            
            f"🏆 Лучшие показатели:\n"
            f"├ Лучшая пробежка: {best_stats['best_run']:.1f} км\n"
            f"├ Всего пробежек: {best_stats['total_runs']}\n"
            f"└ Общая дистанция: {best_stats['total_km']:.1f} км\n\n"
            
            f"🔄 Последние пробежки:\n"
        )
        
        # Добавляем последние пробежки
        for run in recent_runs:
            stats_text += f"└ {run['date'].strftime('%Y-%m-%d')}: {run['distance_km']} км\n"
        
        # Добавляем эмодзи реакции
        stats_text += "\n👍 HD"
        
        bot.reply_to(message, stats_text)
        logger.debug(f"Detailed stats shown for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in show_stats: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при получении статистики") 

@bot.message_handler(commands=['chatgoal', 'setchatgoal'])
def show_chat_goal(message):
    """Показывает или устанавливает статистику по общей цели чата"""
    try:
        print(f"\n>>> Processing chat goal command: {message.text}")
        chat_id = str(message.chat.id)
        if chat_id.startswith('-100'):
            chat_id = chat_id[4:]
        year = datetime.now().year
        print(f">>> Chat ID (cleaned): {chat_id}")
        
        # Если это команда установки цели
        if message.text.startswith('/setchatgoal'):
            bot.reply_to(message, "🎯 Укажите цель в километрах для чата на 2025 год:")
            bot.register_next_step_handler(message, process_chat_goal_km)
            return
            
        # Если это команда просмотра статистики
        challenge = Challenge.get_chat_challenge(chat_id, year)
        print(f">>> Got challenge: {challenge.__dict__ if challenge else None}")
        
        if not challenge:
            bot.reply_to(message, "❌ В этом чате не установлена общая цель на текущий год")
            return
            
        # Получаем статистику участников
        total_km = challenge.get_total_progress()
        participants_count = challenge.get_participants_count()
        print(f">>> Total km: {total_km}, Participants: {participants_count}")
        
        # Формируем прогресс-бар
        progress = (total_km / challenge.goal_km * 100) if challenge.goal_km > 0 else 0
        progress_bar = "█" * int(progress / 5) + "▒" * (20 - int(progress / 5))
        
        stats_text = (
            f"📊 Статистика чата на {year} год:\n\n"
            f"🎯 Цель: {challenge.goal_km:.1f} км\n"
            f"👥 Общий прогресс: {total_km:.1f} км\n"
            f"📈 Выполнено: {progress:.1f}%\n"
            f"👤 Участников: {participants_count}"
        )
        
        bot.reply_to(message, stats_text)
        print(">>> Stats sent successfully")
        
    except Exception as e:
        print(f">>> ERROR in show_chat_goal: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка при получении статистики чата") 

def process_chat_goal_km(message):
    """Обрабатывает ввод километража для цели чата"""
    try:
        print(f"\n>>> Processing chat goal value: {message.text}")
        chat_id = str(message.chat.id)
        if chat_id.startswith('-100'):
            chat_id = chat_id[4:]
        year = datetime.now().year
        print(f">>> Chat ID (cleaned): {chat_id}")
        
        try:
            goal_km = float(message.text.replace(',', '.'))
            if goal_km <= 0:
                raise ValueError
            print(f">>> Goal value: {goal_km}")
        except ValueError:
            bot.reply_to(message, "❌ Пожалуйста, введите положительное число километров")
            return
            
        # Создаем новый челлендж чата
        challenge = Challenge(
            title=f"Общая цель чата на {year} год",
            goal_km=goal_km,
            start_date=f"{year}-01-01",
            end_date=f"{year}-12-31",
            chat_id=chat_id,
            is_system=False  # Общие челленджи не являются системными
        )
        
        print(f">>> Saving challenge: {challenge.__dict__}")
        challenge.save()
        print(">>> Challenge saved")
        
        total_km = challenge.get_total_progress()
        participants_count = challenge.get_participants_count()
        progress = (total_km / goal_km * 100) if goal_km > 0 else 0
        
        bot.reply_to(
            message,
            f"✅ Установлена общая цель чата на {year} год!\n\n"
            f"🎯 Цель: {goal_km:.1f} км\n"
            f"👥 Текущий прогресс: {total_km:.1f} км\n"
            f"📈 Выполнено: {progress:.1f}%\n"
            f"👤 Участников: {participants_count}\n\n"
            f"Все участники чата автоматически участвуют в достижении цели."
        )
            
    except Exception as e:
        print(f">>> ERROR in process_chat_goal_km: {str(e)}")
        bot.reply_to(message, "❌ Произошла ошибка при установке цели") 