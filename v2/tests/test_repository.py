from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from app.db import create_database, create_schema
from app.periods import Period, period_range
from app.repository import (
    RunInput,
    add_run,
    get_ranking,
    get_totals,
    get_user_stats,
    soft_delete_owned_run,
)


@pytest_asyncio.fixture
async def database():
    database = create_database("sqlite+aiosqlite:///:memory:")
    await create_schema(database.engine)
    yield database
    await database.engine.dispose()


def run_input(
    *,
    chat_id: int,
    user_id: int,
    message_id: int,
    distance: str,
    run_date: date = date(2026, 7, 30),
) -> RunInput:
    return RunInput(
        chat_id=chat_id,
        chat_title=f"Chat {chat_id}",
        user_id=user_id,
        username=f"runner{user_id}",
        display_name=f"Runner {user_id}",
        telegram_message_id=message_id,
        distance_km=Decimal(distance),
        run_date=run_date,
    )


@pytest.mark.asyncio
async def test_ranking_is_isolated_by_chat_and_period(database) -> None:
    async with database.sessions() as session:
        await add_run(
            session,
            run_input(chat_id=1, user_id=10, message_id=1, distance="5.00"),
        )
        await add_run(
            session,
            run_input(chat_id=1, user_id=20, message_id=2, distance="8.00"),
        )
        await add_run(
            session,
            run_input(
                chat_id=1,
                user_id=10,
                message_id=3,
                distance="20.00",
                run_date=date(2026, 6, 1),
            ),
        )
        await add_run(
            session,
            run_input(chat_id=2, user_id=10, message_id=1, distance="99.00"),
        )
        await session.commit()

        ranking = await get_ranking(
            session,
            chat_id=1,
            date_range=period_range(Period.MONTH, date(2026, 7, 30)),
        )
        totals = await get_totals(
            session,
            chat_id=1,
            date_range=period_range(Period.MONTH, date(2026, 7, 30)),
        )

    assert [entry.user_id for entry in ranking] == [20, 10]
    assert [entry.total_km for entry in ranking] == [Decimal("8.00"), Decimal("5.00")]
    assert totals.total_km == Decimal("13.00")
    assert totals.runners_count == 2


@pytest.mark.asyncio
async def test_duplicate_telegram_message_is_idempotent(database) -> None:
    async with database.sessions() as session:
        data = run_input(chat_id=1, user_id=10, message_id=42, distance="5.00")
        first, first_created = await add_run(session, data)
        await session.commit()
        second, second_created = await add_run(session, data)

    assert first_created is True
    assert second_created is False
    assert second.id == first.id


@pytest.mark.asyncio
async def test_soft_delete_updates_stats_and_checks_owner(database) -> None:
    async with database.sessions() as session:
        run, _ = await add_run(
            session,
            run_input(chat_id=1, user_id=10, message_id=1, distance="5.00"),
        )
        await session.commit()

        wrong_owner = await soft_delete_owned_run(
            session,
            run_id=run.id,
            chat_id=1,
            user_id=20,
        )
        deleted = await soft_delete_owned_run(
            session,
            run_id=run.id,
            chat_id=1,
            user_id=10,
        )
        await session.commit()
        stats = await get_user_stats(
            session,
            chat_id=1,
            user_id=10,
            date_range=period_range(Period.ALL, date(2026, 7, 30)),
        )

    assert wrong_owner is None
    assert deleted is not None
    assert stats.total_km == Decimal("0.00")
    assert stats.runs_count == 0
