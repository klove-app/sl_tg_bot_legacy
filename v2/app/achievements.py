from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import AchievementAward, Run, Runner
from app.periods import DateRange

logger = logging.getLogger("runtracker.achievements")


@dataclass(frozen=True)
class AchievementDefinition:
    code: str
    emoji: str
    title: str


@dataclass(frozen=True)
class AwardView:
    user_id: int
    display_name: str
    definition: AchievementDefinition
    reference_date: date


@dataclass(frozen=True)
class RunnerStatus:
    emoji: str
    title: str


ACHIEVEMENTS = (
    AchievementDefinition("club_2", "🟢", "Клуб 2 км"),
    AchievementDefinition("club_5", "🔵", "Клуб 5 км"),
    AchievementDefinition("club_10", "🟣", "Клуб 10 км"),
    AchievementDefinition("couch_1", "🛋️", "С дивана I степени"),
    AchievementDefinition("couch_2", "🛋️", "С дивана II степени"),
    AchievementDefinition("couch_3", "🛋️", "С дивана III степени"),
    AchievementDefinition("not_accidental", "👟", "Это уже не случайность"),
    AchievementDefinition("three_outings", "📅", "Три выхода"),
    AchievementDefinition("system_4w", "🔁", "А это уже система"),
    AchievementDefinition("total_100", "💯", "Намотал сотню"),
    AchievementDefinition("total_500", "🛰️", "Пятьсот, полёт нормальный"),
    AchievementDefinition("total_1000", "🌍", "Тысяча километров леса"),
)
ACHIEVEMENT_BY_CODE = {item.code: item for item in ACHIEVEMENTS}


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _eligible_achievements(runs: list[Run]) -> dict[str, date]:
    if not runs:
        return {}

    eligible: dict[str, date] = {}
    for threshold, code in (
        (Decimal("2"), "club_2"),
        (Decimal("5"), "club_5"),
        (Decimal("10"), "club_10"),
    ):
        qualifying = [run for run in runs if run.distance_km >= threshold]
        if qualifying:
            eligible[code] = qualifying[0].run_date

    couch_start: date | None = None
    previous_run_date: date | None = None
    for run in runs:
        gap = (
            (run.run_date - previous_run_date).days
            if previous_run_date is not None
            else None
        )
        if run.distance_km >= Decimal("2") and (gap is None or gap >= 30):
            couch_start = run.run_date
            break
        previous_run_date = run.run_date
    if couch_start is not None:
        eligible["couch_1"] = couch_start
        comeback_runs = [
            run for run in runs if 0 <= (run.run_date - couch_start).days <= 30
        ]
        if sum((run.run_date - couch_start).days <= 10 for run in comeback_runs) >= 2:
            eligible["couch_2"] = comeback_runs[1].run_date
        if len(comeback_runs) >= 4:
            eligible["couch_3"] = comeback_runs[3].run_date

    if len(runs) >= 3:
        eligible["not_accidental"] = runs[2].run_date

    weekly_runs: dict[date, list[Run]] = {}
    for run in runs:
        weekly_runs.setdefault(_week_start(run.run_date), []).append(run)
    weekly_counts = Counter(
        {week: len(week_runs) for week, week_runs in weekly_runs.items()}
    )
    three_run_weeks = [week for week, count in weekly_counts.items() if count >= 3]
    if three_run_weeks:
        first_week = min(three_run_weeks)
        eligible["three_outings"] = weekly_runs[first_week][2].run_date

    active_weeks = set(weekly_counts)
    four_week_finishes = [
        week
        for week in active_weeks
        if all(week - timedelta(days=7 * offset) in active_weeks for offset in range(4))
    ]
    if four_week_finishes:
        first_finish = min(four_week_finishes)
        eligible["system_4w"] = weekly_runs[first_finish][0].run_date

    total_km = sum((Decimal(str(run.distance_km)) for run in runs), Decimal("0"))
    for threshold, code in (
        (Decimal("100"), "total_100"),
        (Decimal("500"), "total_500"),
        (Decimal("1000"), "total_1000"),
    ):
        if total_km >= threshold:
            running_total = Decimal("0")
            for run in runs:
                running_total += Decimal(str(run.distance_km))
                if running_total >= threshold:
                    eligible[code] = run.run_date
                    break

    return eligible


async def evaluate_achievements(
    session: AsyncSession,
    *,
    chat_id: int,
    user_id: int,
) -> list[AchievementDefinition]:
    runs = list(
        (
            await session.scalars(
                select(Run)
                .where(
                    Run.chat_id == chat_id,
                    Run.user_id == user_id,
                    Run.deleted_at.is_(None),
                )
                .order_by(Run.run_date.asc(), Run.created_at.asc(), Run.id.asc())
            )
        ).all()
    )
    eligible = _eligible_achievements(runs)
    if not eligible:
        return []

    existing = set(
        (
            await session.scalars(
                select(AchievementAward.code).where(
                    AchievementAward.chat_id == chat_id,
                    AchievementAward.user_id == user_id,
                    AchievementAward.period_key == "lifetime",
                )
            )
        ).all()
    )
    new_awards: list[AchievementDefinition] = []
    for definition in ACHIEVEMENTS:
        reference_date = eligible.get(definition.code)
        if reference_date is None or definition.code in existing:
            continue
        session.add(
            AchievementAward(
                chat_id=chat_id,
                user_id=user_id,
                code=definition.code,
                period_key="lifetime",
                reference_date=reference_date,
            )
        )
        new_awards.append(definition)
    await session.flush()
    return new_awards


async def backfill_achievements(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with sessions() as session:
        runners = list(
            (
                await session.execute(
                    select(Runner.chat_id, Runner.user_id).order_by(
                        Runner.chat_id,
                        Runner.user_id,
                    )
                )
            ).all()
        )
        awards_count = 0
        for runner in runners:
            awards_count += len(
                await evaluate_achievements(
                    session,
                    chat_id=runner.chat_id,
                    user_id=runner.user_id,
                )
            )
        await session.commit()
    logger.info("Achievement backfill completed: %s new awards", awards_count)


async def get_user_awards(
    session: AsyncSession,
    *,
    chat_id: int,
    user_id: int,
) -> list[AchievementDefinition]:
    codes = list(
        (
            await session.scalars(
                select(AchievementAward.code)
                .where(
                    AchievementAward.chat_id == chat_id,
                    AchievementAward.user_id == user_id,
                    AchievementAward.period_key == "lifetime",
                )
                .order_by(
                    AchievementAward.reference_date.desc(),
                    AchievementAward.code.asc(),
                )
            )
        ).all()
    )
    return [ACHIEVEMENT_BY_CODE[code] for code in codes if code in ACHIEVEMENT_BY_CODE]


async def get_period_awards(
    session: AsyncSession,
    *,
    chat_id: int,
    date_range: DateRange,
) -> list[AwardView]:
    conditions = [
        AchievementAward.chat_id == chat_id,
        AchievementAward.period_key == "lifetime",
        AchievementAward.reference_date <= date_range.end,
    ]
    if date_range.start is not None:
        conditions.append(AchievementAward.reference_date >= date_range.start)
    rows = (
        await session.execute(
            select(
                AchievementAward.user_id,
                Runner.display_name,
                AchievementAward.code,
                AchievementAward.reference_date,
            )
            .join(
                Runner,
                and_(
                    Runner.chat_id == AchievementAward.chat_id,
                    Runner.user_id == AchievementAward.user_id,
                ),
            )
            .where(*conditions)
            .order_by(AchievementAward.reference_date, Runner.display_name)
        )
    ).all()
    return [
        AwardView(
            user_id=row.user_id,
            display_name=row.display_name,
            definition=ACHIEVEMENT_BY_CODE[row.code],
            reference_date=row.reference_date,
        )
        for row in rows
        if row.code in ACHIEVEMENT_BY_CODE
    ]


async def get_runner_status(
    session: AsyncSession,
    *,
    chat_id: int,
    user_id: int,
    today: date,
) -> RunnerStatus:
    run_dates = list(
        (
            await session.scalars(
                select(Run.run_date)
                .where(
                    Run.chat_id == chat_id,
                    Run.user_id == user_id,
                    Run.deleted_at.is_(None),
                )
                .order_by(Run.run_date.desc(), Run.created_at.desc())
            )
        ).all()
    )
    if not run_dates:
        return RunnerStatus("🆕", "Новая ячейка")

    last_run = run_dates[0]
    days_silent = (today - last_run).days
    if days_silent >= 60:
        return RunnerStatus("😴", "Спящая ячейка")
    if len(run_dates) >= 2 and (last_run - run_dates[1]).days >= 60 and days_silent <= 14:
        return RunnerStatus("⚡", "Снова в эфире")
    if len(run_dates) == 1 and days_silent <= 30:
        return RunnerStatus("🆕", "Новая ячейка")
    runs_last_30 = sum((today - run_date).days <= 30 for run_date in run_dates)
    if days_silent <= 14 and runs_last_30 >= 3:
        return RunnerStatus("🌲", "Полевой сотрудник")
    if days_silent <= 14:
        return RunnerStatus("🟢", "На связи")
    return RunnerStatus("📴", "Вне эфира")


async def get_sleeping_runners(
    session: AsyncSession,
    *,
    chat_id: int,
    today: date,
) -> list[str]:
    cutoff = today - timedelta(days=60)
    rows = (
        await session.execute(
            select(Runner.display_name)
            .join(
                Run,
                and_(
                    Run.chat_id == Runner.chat_id,
                    Run.user_id == Runner.user_id,
                    Run.deleted_at.is_(None),
                ),
            )
            .where(Runner.chat_id == chat_id)
            .group_by(Runner.user_id, Runner.display_name)
            .having(func.max(Run.run_date) <= cutoff)
            .order_by(Runner.display_name)
        )
    ).all()
    return [row.display_name for row in rows]
