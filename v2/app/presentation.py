from __future__ import annotations

import html
from datetime import date
from decimal import Decimal

from app.achievements import AchievementDefinition, AwardView
from app.journey import JOURNEY_TITLE, JourneyCheckpoint, JourneyPlace, JourneyProgress
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


def format_percent(value: Decimal) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def journey_progress_lines(
    progress: JourneyProgress,
    *,
    newly_reached: list[JourneyCheckpoint] | None = None,
    newly_reached_places: list[JourneyPlace] | None = None,
    include_title: bool = True,
) -> list[str]:
    lines: list[str] = []
    if include_title:
        lines.extend(
            [
                f"🏔 <b>{JOURNEY_TITLE}</b> · 2026",
                "Парк Краснодар → Шамони",
            ]
        )
    lines.append(
        f"🛣 Вместе: <b>{format_km(progress.total_km)} / "
        f"{format_km(progress.target_km)} км</b> · {format_percent(progress.percent)}%"
    )
    if progress.completed:
        lines.append("🏁 <b>Финиш в Шамони достигнут!</b>")
        if progress.overage_km > 0:
            lines.append(f"✨ Сверх цели: <b>{format_km(progress.overage_km)} км</b>")
    elif progress.next_checkpoint is not None:
        lines.append(
            f"📖 Следующая глава: <b>{progress.next_checkpoint.title}</b> · "
            f"осталось {format_km(progress.remaining_to_next_km)} км"
        )

    lines.append(
        f"📍 Сейчас рядом: <b>{html.escape(progress.current_waypoint.title)}</b> · "
        f"{format_km(progress.current_waypoint.distance_km)} км маршрута"
    )
    if progress.next_waypoint is not None:
        lines.append(
            f"🎯 Через {format_km(progress.remaining_to_next_waypoint_km)} км: "
            f"<b>{html.escape(progress.next_waypoint.title)}</b>"
        )

    if newly_reached_places:
        lines.extend(["", "🧭 <b>Новая остановка на маршруте!</b>"])
        for place in newly_reached_places:
            lines.extend([f"📍 <b>{place.title}</b>", f"💡 {place.fact}"])
    else:
        lines.extend(
            [
                f"🧭 Большая остановка: <b>{progress.current_place.title}</b>",
                f"💡 {progress.current_place.fact}",
            ]
        )
    if progress.next_place is not None:
        lines.append(
            f"Большая цель: {progress.next_place.title} · "
            f"{format_km(progress.remaining_to_next_place_km)} км"
        )

    if newly_reached:
        lines.extend(
            [
                "",
                "🎉 <b>Новая точка маршрута!</b>",
                *(
                    f"📌 {checkpoint.title} · {format_km(checkpoint.distance_km)} км"
                    for checkpoint in newly_reached
                ),
            ]
        )
    return lines


def render_journey_progress(
    progress: JourneyProgress,
    *,
    newly_reached: list[JourneyCheckpoint] | None = None,
    newly_reached_places: list[JourneyPlace] | None = None,
) -> str:
    return "\n".join(
        [
            *journey_progress_lines(
                progress,
                newly_reached=newly_reached,
                newly_reached_places=newly_reached_places,
            ),
            "",
            "🏆 /top · 👤 /me · ↩️ /undo",
        ]
    )


def render_run_confirmation(
    *,
    distance_km: Decimal,
    run_date: date,
    note: str | None,
    month_stats: UserStats,
    league: League | None,
    league_place: int | None,
    league_runners_count: int,
    new_awards: list[AchievementDefinition] | None = None,
    journey_progress: JourneyProgress | None = None,
    new_journey_checkpoints: list[JourneyCheckpoint] | None = None,
    new_journey_places: list[JourneyPlace] | None = None,
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

    if new_awards:
        lines.extend(
            [
                "",
                "🎖 <b>Новые награды</b>",
                *(f"{award.emoji} {award.title}" for award in new_awards),
            ]
        )

    if journey_progress is not None:
        lines.extend(
            [
                "",
                *journey_progress_lines(
                    journey_progress,
                    newly_reached=new_journey_checkpoints,
                    newly_reached_places=new_journey_places,
                ),
            ]
        )

    lines.extend(
        [
            "",
            "🗺 /journey · 🏆 /top · 👤 /me · ↩️ /undo",
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
    title: str | None = None,
) -> str:
    ranking_title = title or PERIOD_TITLES[period]
    active_runners = pluralize(
        totals.runners_count,
        "активный участник",
        "активных участника",
        "активных участников",
    )
    lines = [f"🏆 <b>Беговой рейтинг · {ranking_title}</b>"]
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


_COMPACT_AWARD_TITLES = {
    "club_2": "2 км",
    "club_5": "5 км",
    "club_10": "10 км",
    "couch_1": "Диван I",
    "couch_2": "Диван II",
    "couch_3": "Диван III",
    "not_accidental": "Не случайность",
    "three_outings": "3 выхода",
    "system_4w": "Система",
    "total_100": "100 км",
    "total_500": "500 км",
    "total_1000": "1000 км",
}


def _compact_award_rows(
    runner_awards: list[AwardView], *, max_length: int = 58
) -> list[str]:
    chips = [
        (
            f"{award.definition.emoji} "
            f"{_COMPACT_AWARD_TITLES.get(award.definition.code, award.definition.title)}"
        )
        for award in runner_awards
    ]
    rows: list[str] = []
    current = ""
    for chip in chips:
        candidate = f"{current} · {chip}" if current else chip
        if current and len(candidate) > max_length:
            rows.append(f"↳ {current}")
            current = chip
        else:
            current = candidate
    if current:
        rows.append(f"↳ {current}")
    return rows


def _grouped_award_lines(awards: list[AwardView]) -> list[str]:
    grouped: dict[int, tuple[str, list[AwardView]]] = {}
    for award in awards:
        if award.user_id not in grouped:
            grouped[award.user_id] = (award.display_name, [])
        grouped[award.user_id][1].append(award)

    lines: list[str] = []
    for index, (display_name, runner_awards) in enumerate(grouped.values()):
        if index:
            lines.append("")
        lines.extend(
            [
                (
                    f"👤 <b>{html.escape(display_name)}</b> · "
                    f"{pluralize(len(runner_awards), 'награда', 'награды', 'наград')}"
                ),
                *_compact_award_rows(runner_awards),
            ]
        )
    return lines


def render_period_summary(
    *,
    period: Period,
    date_range: DateRange,
    rankings: dict[League, list[RankingEntry]],
    totals: Totals,
    awards: list[AwardView] | None = None,
    sleeping_runners: list[str] | None = None,
    journey_progress: JourneyProgress | None = None,
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
    if journey_progress is not None:
        lines.extend(["", *journey_progress_lines(journey_progress)])
    if awards:
        lines.extend(["", f"🎖 <b>Новые награды</b> · {len(awards)}"])
        lines.extend(_grouped_award_lines(awards))
    if period is Period.MONTH:
        cup_lines: list[str] = []
        tempo = next(
            (entry for entry in rankings.get(League.TEMPO, []) if entry.runs_count),
            None,
        )
        trail = next(
            (entry for entry in rankings.get(League.TRAIL, []) if entry.runs_count),
            None,
        )
        if tempo is not None:
            cup_lines.append(
                f"🔥 Держит Темп — <b>{html.escape(tempo.display_name)}</b>"
            )
        if trail is not None:
            cup_lines.append(
                f"🌱 Хозяин Тропы — <b>{html.escape(trail.display_name)}</b>"
            )
        if cup_lines:
            lines.extend(["", "🏅 <b>Звания месяца</b>", *cup_lines])
        if sleeping_runners:
            visible = sleeping_runners[:10]
            names = ", ".join(html.escape(name) for name in visible)
            if len(sleeping_runners) > len(visible):
                names += f" и ещё {len(sleeping_runners) - len(visible)}"
            lines.extend(["", f"😴 <b>Спящие ячейки:</b> {names}"])
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
