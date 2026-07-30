from __future__ import annotations

import html
from datetime import date
from decimal import Decimal

from app.periods import Period
from app.repository import RankingEntry, Totals, UserStats

MONTH_NAMES = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

PERIOD_TITLES = {
    Period.WEEK: "Неделя",
    Period.MONTH: "Месяц",
    Period.YEAR: "Год",
    Period.ALL: "Всё время",
}


def format_km(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def pluralize(value: int, one: str, few: str, many: str) -> str:
    remainder_100 = value % 100
    remainder_10 = value % 10
    if 11 <= remainder_100 <= 14:
        word = many
    elif remainder_10 == 1:
        word = one
    elif 2 <= remainder_10 <= 4:
        word = few
    else:
        word = many
    return f"{value} {word}"


def format_run_date(value: date) -> str:
    return f"{value.day} {MONTH_NAMES[value.month - 1]}"


def render_run_confirmation(
    *,
    distance_km: Decimal,
    run_date: date,
    note: str | None,
    month_stats: UserStats,
    month_place: int | None,
    runners_count: int,
) -> str:
    lines = [
        "✅ <b>Пробежка записана</b>",
        "",
        f"🏃 <b>{format_km(distance_km)} км</b> · {format_run_date(run_date)}",
    ]
    if note:
        lines.append(f"📝 {html.escape(note)}")

    lines.extend(
        [
            "",
            (
                f"📊 За месяц: <b>{format_km(month_stats.total_km)} км</b> · "
                f"{pluralize(month_stats.runs_count, 'пробежка', 'пробежки', 'пробежек')}"
            ),
        ]
    )
    if month_place is not None:
        lines.append(
            f"🏅 В рейтинге: <b>№{month_place}</b> из {runners_count}"
        )

    lines.extend(
        [
            "",
            "🏆 /top · 👤 /me · ↩️ /undo",
        ]
    )
    return "\n".join(lines)


def render_ranking(
    *,
    period: Period,
    ranking: list[RankingEntry],
    totals: Totals,
) -> str:
    title = PERIOD_TITLES[period]
    lines = [f"🏆 <b>Рейтинг · {title}</b>", ""]
    if not ranking:
        lines.extend(
            [
                "Пока здесь пусто.",
                "Упомяните бота и добавьте первую пробежку 👟",
            ]
        )
        return "\n".join(lines)

    medals = ["🥇", "🥈", "🥉"]
    for index, entry in enumerate(ranking, start=1):
        place = medals[index - 1] if index <= len(medals) else f"{index}."
        name = html.escape(entry.display_name)
        runs = pluralize(entry.runs_count, "пробежка", "пробежки", "пробежек")
        lines.append(
            f"{place} <b>{name}</b> — <b>{format_km(entry.total_km)} км</b> · {runs}"
        )

    lines.extend(
        [
            "",
            (
                f"👟 {pluralize(totals.runners_count, 'участник', 'участника', 'участников')}"
                f" · {pluralize(totals.runs_count, 'пробежка', 'пробежки', 'пробежек')}"
            ),
            f"🛣 Вместе: <b>{format_km(totals.total_km)} км</b>",
            "",
            "👤 /me · ↩️ /undo",
        ]
    )
    return "\n".join(lines)
