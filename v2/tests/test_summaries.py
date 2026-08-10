from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db import create_database, create_schema
from app.periods import Period
from app.repository import RunInput, add_run
from app.summaries import (
    deliver_due_summaries,
    due_summary_specs,
    split_telegram_message,
)


def summary_settings():
    return SimpleNamespace(
        summaries_enabled=True,
        summary_hour=9,
        monthly_summary_minute=10,
    )


def test_weekly_summary_is_due_on_monday_for_closed_week() -> None:
    specs = due_summary_specs(
        datetime(2026, 8, 10, 9, 0),
        summary_settings(),
    )

    assert [(spec.kind, spec.period) for spec in specs] == [("weekly", Period.WEEK)]
    assert specs[0].date_range.start.isoformat() == "2026-08-03"
    assert specs[0].date_range.end.isoformat() == "2026-08-09"


def test_monthly_summary_is_due_on_first_day_for_closed_month() -> None:
    specs = due_summary_specs(
        datetime(2026, 9, 1, 9, 10),
        summary_settings(),
    )

    assert [(spec.kind, spec.period) for spec in specs] == [("monthly", Period.MONTH)]
    assert specs[0].date_range.start.isoformat() == "2026-08-01"
    assert specs[0].date_range.end.isoformat() == "2026-08-31"


def test_long_summary_is_split_on_line_boundaries() -> None:
    chunks = split_telegram_message("one\ntwo\nthree", max_length=7)

    assert chunks == ["one\ntwo", "three"]


@pytest.mark.asyncio
async def test_weekly_summary_is_delivered_only_once() -> None:
    database = create_database("sqlite+aiosqlite:///:memory:")
    await create_schema(database.engine)
    async with database.sessions() as session:
        await add_run(
            session,
            RunInput(
                chat_id=-100,
                chat_title="Беговой чат",
                user_id=1,
                username="ivan",
                display_name="Иван",
                telegram_message_id=1,
                distance_km=Decimal("6.03"),
                run_date=datetime(2026, 8, 9).date(),
            ),
        )
        await session.commit()

    settings = SimpleNamespace(
        summaries_enabled=True,
        summary_hour=9,
        monthly_summary_minute=10,
        bot_timezone="Europe/Moscow",
        allowed_chat_id_set=set(),
    )
    bot = SimpleNamespace(send_message=AsyncMock())
    now = datetime(2026, 8, 10, 9, 0)

    await deliver_due_summaries(bot, database.sessions, settings, now=now)
    await deliver_due_summaries(bot, database.sessions, settings, now=now)

    bot.send_message.assert_awaited_once()
    assert "Итоги недели" in bot.send_message.await_args.args[1]
    assert "Из Кубани к Монблану" in bot.send_message.await_args.args[1]
    assert "6,03 / 2500 км" in bot.send_message.await_args.args[1]
    await database.engine.dispose()
