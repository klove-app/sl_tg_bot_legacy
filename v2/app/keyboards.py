from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.periods import Period


def top_period_keyboard(active: Period) -> InlineKeyboardMarkup:
    labels = {
        Period.WEEK: "Неделя",
        Period.MONTH: "Месяц",
        Period.YEAR: "Год",
        Period.ALL: "Всё время",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("• " if period is active else "") + label,
                    callback_data=f"top:{period.value}",
                )
                for period, label in labels.items()
            ]
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
