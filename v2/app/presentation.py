from __future__ import annotations

import html
from datetime import date
from decimal import Decimal

from app.leagues import LEAGUE_EMOJI, LEAGUE_TITLES, League
from app.periods import DateRange, Period
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
    league: League | None,
    league_place: int | None,
    league_runners_count: int,
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
    if league is not None and league_place is not None:
        lines.append(
            f"{LEAGUE_EMOJI[league]} Лига «{LEAGUE_TITLES[league]}»: "
            f"<b>№{league_place}</b> из {league_runners_count}"
        )

    lines.extend(
        [
            "",
            "🏆 /top · 👤 /me · ↩️ /undo",
        ]
    )
    return "\n".join(lines)


def _league_rows(ranking: list[RankingEntry], *, limit: int | None = None) -> list[str]:
    if not ranking:
        return ["Пока без участников."]

    entries = ranking if limit is None else ranking[:limit]
    medals = ["🥇", "🥈", "🥉"]
    lines: list[str] = []
    for index, entry in enumerate(entries, start=1):
        place = medals[index - 1] if index <= len(medals) else f"{index}."
        name = html.escape(entry.display_name)
        runs = pluralize(entry.runs_count, "пробежка", "пробежки", "пробежек")
        lines.append(
            f"{place} <b>{name}</b> — <b>{format_km(entry.total_km)} км</b> · {runs}"
        )
    if limit is not None and len(ranking) > limit:
        lines.append(f"…и ещё {len(ranking) - limit}")
    return lines


def render_league_ranking(
    *,
    period: Period,
    rankings: dict[League, list[RankingEntry]],
    totals: Totals,
    limit_per_league: int = 10,
) -> str:
    title = PERIOD_TITLES[period]
    active_runners = pluralize(
        totals.runners_count,
        "активный участник",
        "активных участника",
        "активных участников",
    )
    lines = [f"🏆 <b>Беговой рейтинг · {title}</b>"]
    for league in (League.TEMPO, League.TRAIL):
        lines.extend(
            [
                "",
                f"{LEAGUE_EMOJI[league]} <b>Лига «{LEAGUE_TITLES[league]}»</b>",
                *_league_rows(rankings.get(league, []), limit=limit_per_league),
            ]
        )

    lines.extend(
        [
            "",
            (
                f"👟 {active_runners}"
                f" · {pluralize(totals.runs_count, 'пробежка', 'пробежки', 'пробежек')}"
            ),
            f"🛣 Вместе: <b>{format_km(totals.total_km)} км</b>",
            "",
            "👤 /me · ↩️ /undo",
        ]
    )
    return "\n".join(lines)


def _date_range_label(date_range: DateRange) -> str:
    if date_range.start is None:
        return format_run_date(date_range.end)
    if date_range.start == date_range.end:
        return format_run_date(date_range.end)
    if date_range.start.month == date_range.end.month:
        return (
            f"{date_range.start.day}–{date_range.end.day} "
            f"{MONTH_NAMES[date_range.end.month - 1]}"
        )
    return f"{format_run_date(date_range.start)} – {format_run_date(date_range.end)}"


def render_period_summary(
    *,
    period: Period,
    date_range: DateRange,
    rankings: dict[League, list[RankingEntry]],
    totals: Totals,
) -> str:
    summary_title = "Итоги недели" if period is Period.WEEK else "Итоги месяца"
    active_runners = pluralize(
        totals.runners_count,
        "активный участник",
        "активных участника",
        "активных участников",
    )
    lines = [f"🌲 <b>{summary_title}</b> · {_date_range_label(date_range)}"]
    for league in (League.TEMPO, League.TRAIL):
        lines.extend(
            [
                "",
                f"{LEAGUE_EMOJI[league]} <b>Лига «{LEAGUE_TITLES[league]}»</b>",
                *_league_rows(rankings.get(league, [])),
            ]
        )

    lines.extend(
        [
            "",
            f"🔥 {active_runners}",
            (
                f"🏃 {pluralize(totals.runs_count, 'пробежка', 'пробежки', 'пробежек')}"
                f" · <b>{format_km(totals.total_km)} км</b> вместе"
            ),
        ]
    )
    if period is Period.MONTH:
        lines.extend(
            [
                "",
                "⬆️ Лучшие активные бегуны «Тропы» переходят в «Темп» в новом месяце.",
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
