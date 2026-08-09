from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievements import get_period_awards, get_sleeping_runners
from app.config import Settings
from app.leagues import League
from app.periods import (
    DateRange,
    Period,
    month_date_range,
    month_start,
    previous_month_start,
    week_date_range,
)
from app.presentation import render_period_summary
from app.repository import (
    ensure_month_leagues,
    get_chat_ids,
    get_league_ranking,
    get_totals,
    mark_summary_delivered,
    summary_was_delivered,
)

logger = logging.getLogger("runtracker.summaries")


@dataclass(frozen=True)
class SummarySpec:
    kind: str
    period: Period
    date_range: DateRange


def due_summary_specs(now: datetime, settings: Settings) -> list[SummarySpec]:
    if not settings.summaries_enabled:
        return []

    today = now.date()
    due: list[SummarySpec] = []
    if today.weekday() == 0 and now.hour >= settings.summary_hour:
        due.append(
            SummarySpec(
                kind="weekly",
                period=Period.WEEK,
                date_range=week_date_range(today - timedelta(days=1)),
            )
        )

    monthly_due = now.hour > settings.summary_hour or (
        now.hour == settings.summary_hour
        and now.minute >= settings.monthly_summary_minute
    )
    if today.day == 1 and monthly_due:
        prior_month = previous_month_start(today)
        due.append(
            SummarySpec(
                kind="monthly",
                period=Period.MONTH,
                date_range=month_date_range(prior_month),
            )
        )
    return due


def split_telegram_message(text: str, max_length: int = 3900) -> list[str]:
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_length:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = line
    if current:
        chunks.append(current)
    return chunks


async def _summary_text(
    session: AsyncSession,
    *,
    chat_id: int,
    spec: SummarySpec,
) -> tuple[str, int]:
    membership_month = month_start(spec.date_range.end)
    await ensure_month_leagues(
        session,
        chat_id=chat_id,
        membership_month=membership_month,
        seed_end=spec.date_range.end,
    )
    rankings = {
        league: await get_league_ranking(
            session,
            chat_id=chat_id,
            membership_month=membership_month,
            league=league,
            date_range=spec.date_range,
        )
        for league in League
    }
    totals = await get_totals(
        session,
        chat_id=chat_id,
        date_range=spec.date_range,
    )
    awards = await get_period_awards(
        session,
        chat_id=chat_id,
        date_range=spec.date_range,
    )
    sleeping_runners = (
        await get_sleeping_runners(
            session,
            chat_id=chat_id,
            today=spec.date_range.end,
        )
        if spec.period is Period.MONTH
        else []
    )
    return (
        render_period_summary(
            period=spec.period,
            date_range=spec.date_range,
            rankings=rankings,
            totals=totals,
            awards=awards,
            sleeping_runners=sleeping_runners,
        ),
        totals.runs_count,
    )


async def deliver_due_summaries(
    bot: Bot,
    sessions: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    now: datetime | None = None,
) -> None:
    local_now = now or datetime.now(ZoneInfo(settings.bot_timezone))
    specs = due_summary_specs(local_now, settings)
    if not specs:
        return

    async with sessions() as session:
        chat_ids = await get_chat_ids(session)

    allowed = settings.allowed_chat_id_set
    for chat_id in chat_ids:
        if allowed and chat_id not in allowed:
            continue
        for spec in specs:
            async with sessions() as session:
                try:
                    period_start = spec.date_range.start
                    if period_start is None:
                        continue
                    if await summary_was_delivered(
                        session,
                        chat_id=chat_id,
                        summary_kind=spec.kind,
                        period_start=period_start,
                    ):
                        continue

                    text, runs_count = await _summary_text(
                        session,
                        chat_id=chat_id,
                        spec=spec,
                    )
                    if runs_count:
                        for chunk in split_telegram_message(text):
                            await bot.send_message(chat_id, chunk)
                    await mark_summary_delivered(
                        session,
                        chat_id=chat_id,
                        summary_kind=spec.kind,
                        period_start=period_start,
                        period_end=spec.date_range.end,
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    logger.exception(
                        "Could not deliver %s summary to chat %s",
                        spec.kind,
                        chat_id,
                    )


async def summary_loop(
    bot: Bot,
    sessions: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    while True:
        try:
            await deliver_due_summaries(bot, sessions, settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled summary check failed")
        await asyncio.sleep(60)


async def stop_summary_task(task: asyncio.Task[None]) -> None:
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
