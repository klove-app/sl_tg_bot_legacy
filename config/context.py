from typing import Dict, Any

# Словарь для хранения глобального контекста
GLOBAL_CONTEXT: Dict[str, Any] = {
    "system_info": {
        "description": "Я - ваш AI-ассистент, специализирующийся на помощи с кодом и разработкой.",
        "capabilities": [
            "Анализ кода",
            "Рефакторинг",
            "Отладка",
            "Написание документации",
            "Ответы на вопросы по разработке"
        ]
    },
    "project_context": {
        "name": "sl_tg_bot",
        "description": "Telegram бот с расширенной функциональностью",
        "main_components": [
            "Telegram API интеграция",
            "База данных",
            "Обработчики сообщений",
            "Веб-интерфейс"
        ]
    },
    "user_preferences": {
        "language": "russian",
        "code_style": "pep8"
    }
}

def get_context() -> Dict[str, Any]:
    """Получить текущий глобальный контекст."""
    return GLOBAL_CONTEXT

def update_context(key: str, value: Any) -> None:
    """
    Обновить значение в глобальном контексте.
    
    Args:
        key: Ключ для обновления (может быть вложенным, используя точку как разделитель)
        value: Новое значение
    """
    keys = key.split('.')
    current = GLOBAL_CONTEXT
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value 