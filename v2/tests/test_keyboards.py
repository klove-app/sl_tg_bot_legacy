from app.keyboards import top_period_keyboard
from app.periods import Period


def test_top_period_keyboard_uses_compact_two_by_two_layout() -> None:
    keyboard = top_period_keyboard(Period.MONTH)

    assert [[button.text for button in row] for row in keyboard.inline_keyboard] == [
        ["Неделя", "✓ Месяц"],
        ["Год", "Всё время"],
    ]
