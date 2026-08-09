from app.keyboards import top_period_keyboard
from app.periods import Period


def test_top_period_keyboard_only_shows_week_and_month() -> None:
    keyboard = top_period_keyboard(Period.MONTH)

    assert [[button.text for button in row] for row in keyboard.inline_keyboard] == [
        ["Неделя", "✓ Месяц"],
    ]
