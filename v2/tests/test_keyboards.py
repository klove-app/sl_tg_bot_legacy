from datetime import date

from app.keyboards import top_period_keyboard
from app.periods import Period


def test_top_period_keyboard_only_shows_week_and_month() -> None:
    keyboard = top_period_keyboard(Period.MONTH, today=date(2026, 8, 9))

    assert [[button.text for button in row] for row in keyboard.inline_keyboard] == [
        ["Неделя", "✓ Август"],
        ["‹ Июль"],
    ]

    assert [[button.callback_data for button in row] for row in keyboard.inline_keyboard] == [
        ["top:week:0", "top:month:0"],
        ["top:month:-1"],
    ]
