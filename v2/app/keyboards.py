from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.periods import MONTH_NAMES_NOMINATIVE, Period, previous_month_start


def top_period_keyboard(
    active: Period,
    *,
    today: date | None = None,
    month_offset: int = 0,
) -> InlineKeyboardMarkup:
    current = today or date.today()
    prior = previous_month_start(current)
    week = InlineKeyboardButton(
        text=("✓ " if active is Period.WEEK else "") + "Неделя",
        callback_data="top:week:0",
    )
    current_month = InlineKeyboardButton(
        text=("✓ " if active is Period.MONTH and month_offset == 0 else "")
        + MONTH_NAMES_NOMINATIVE[current.month - 1],
        callback_data="top:month:0",
    )
    prior_month = InlineKeyboardButton(
        text=("✓ " if active is Period.MONTH and month_offset == -1 else "")
        + f"‹ {MONTH_NAMES_NOMINATIVE[prior.month - 1]}",
        callback_data="top:month:-1",
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [week, current_month],
            [prior_month],
        ]
    )


def undo_keyboard(run_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=f"undo:{run_id}",
                ),
                InlineKeyboardButton(text="Отмена", callback_data="undo:cancel"),
            ]
        ]
    )
