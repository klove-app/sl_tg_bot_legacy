from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chat, Run, Runner, utc_now
from app.periods import DateRange


@dataclass(frozen=True)
class RunInput:
    chat_id: int
    chat_title: str
    user_id: int
    username: str | None
    display_name: str
    telegram_message_id: int | None
    distance_km: Decimal
    run_date: date
    note: str | None = None
    source: str = "telegram"
    legacy_log_id: int | None = None


@dataclass(frozen=True)
class RankingEntry:
    user_id: int
    display_name: str
    username: str | None
    total_km: Decimal
    runs_count: int
    best_run_km: Decimal


@dataclass(frozen=True)
class Totals:
    total_km: Decimal
    runs_count: int
    runners_count: int


@dataclass(frozen=True)
class UserStats:
    total_km: Decimal
    runs_count: int
    best_run_km: Decimal


def _as_decimal(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _with_period(query: Select, date_range: DateRange) -> Select:
    query = query.where(Run.run_date <= date_range.end)
    if date_range.start is not None:
        query = query.where(Run.run_date >= date_range.start)
    return query


async def upsert_chat_and_runner(session: AsyncSession, data: RunInput) -> None:
    chat = await session.get(Chat, data.chat_id)
    if chat is None:
        session.add(Chat(chat_id=data.chat_id, title=data.chat_title))
    elif chat.title != data.chat_title:
        chat.title = data.chat_title

    runner = await session.get(Runner, (data.chat_id, data.user_id))
    if runner is None:
        session.add(
            Runner(
                chat_id=data.chat_id,
                user_id=data.user_id,
                username=data.username,
                display_name=data.display_name,
            )
        )
    else:
        runner.username = data.username
        runner.display_name = data.display_name


async def add_run(session: AsyncSession, data: RunInput) -> tuple[Run, bool]:
    if data.telegram_message_id is not None:
        existing = await session.scalar(
            select(Run).where(
                Run.chat_id == data.chat_id,
                Run.telegram_message_id == data.telegram_message_id,
            )
        )
        if existing is not None:
            return existing, False

    if data.legacy_log_id is not None:
        existing = await session.scalar(
            select(Run).where(Run.legacy_log_id == data.legacy_log_id)
        )
        if existing is not None:
            return existing, False

    await upsert_chat_and_runner(session, data)
    run = Run(
        chat_id=data.chat_id,
        user_id=data.user_id,
        telegram_message_id=data.telegram_message_id,
        distance_km=data.distance_km,
        run_date=data.run_date,
        note=data.note,
        source=data.source,
        legacy_log_id=data.legacy_log_id,
    )
    session.add(run)
    await session.flush()
    return run, True


async def get_ranking(
    session: AsyncSession,
    *,
    chat_id: int,
    date_range: DateRange,
    limit: int = 10,
) -> list[RankingEntry]:
    query = (
        select(
            Run.user_id,
            Runner.display_name,
            Runner.username,
            func.sum(Run.distance_km).label("total_km"),
            func.count(Run.id).label("runs_count"),
            func.max(Run.distance_km).label("best_run_km"),
        )
        .join(
            Runner,
            and_(
                Runner.chat_id == Run.chat_id,
                Runner.user_id == Run.user_id,
            ),
        )
        .where(
            Run.chat_id == chat_id,
            Run.deleted_at.is_(None),
        )
        .group_by(Run.user_id, Runner.display_name, Runner.username)
        .order_by(func.sum(Run.distance_km).desc(), func.count(Run.id).desc())
        .limit(limit)
    )
    rows = (await session.execute(_with_period(query, date_range))).all()
    return [
        RankingEntry(
            user_id=row.user_id,
            display_name=row.display_name,
            username=row.username,
            total_km=_as_decimal(row.total_km),
            runs_count=int(row.runs_count),
            best_run_km=_as_decimal(row.best_run_km),
        )
        for row in rows
    ]


async def get_totals(
    session: AsyncSession,
    *,
    chat_id: int,
    date_range: DateRange,
) -> Totals:
    query = select(
        func.sum(Run.distance_km).label("total_km"),
        func.count(Run.id).label("runs_count"),
        func.count(func.distinct(Run.user_id)).label("runners_count"),
    ).where(
        Run.chat_id == chat_id,
        Run.deleted_at.is_(None),
    )
    row = (await session.execute(_with_period(query, date_range))).one()
    return Totals(
        total_km=_as_decimal(row.total_km),
        runs_count=int(row.runs_count),
        runners_count=int(row.runners_count),
    )


async def get_user_stats(
    session: AsyncSession,
    *,
    chat_id: int,
    user_id: int,
    date_range: DateRange,
) -> UserStats:
    query = select(
        func.sum(Run.distance_km).label("total_km"),
        func.count(Run.id).label("runs_count"),
        func.max(Run.distance_km).label("best_run_km"),
    ).where(
        Run.chat_id == chat_id,
        Run.user_id == user_id,
        Run.deleted_at.is_(None),
    )
    row = (await session.execute(_with_period(query, date_range))).one()
    return UserStats(
        total_km=_as_decimal(row.total_km),
        runs_count=int(row.runs_count),
        best_run_km=_as_decimal(row.best_run_km),
    )


async def get_latest_active_run(
    session: AsyncSession,
    *,
    chat_id: int,
    user_id: int,
) -> Run | None:
    return await session.scalar(
        select(Run)
        .where(
            Run.chat_id == chat_id,
            Run.user_id == user_id,
            Run.deleted_at.is_(None),
        )
        .order_by(Run.run_date.desc(), Run.created_at.desc(), Run.id.desc())
        .limit(1)
    )


async def soft_delete_owned_run(
    session: AsyncSession,
    *,
    run_id: int,
    chat_id: int,
    user_id: int,
) -> Run | None:
    run = await session.scalar(
        select(Run).where(
            Run.id == run_id,
            Run.chat_id == chat_id,
            Run.user_id == user_id,
            Run.deleted_at.is_(None),
        )
    )
    if run is None:
        return None
    run.deleted_at = utc_now()
    await session.flush()
    return run
