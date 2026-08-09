from datetime import date
from decimal import Decimal

import pytest

from app.achievements import (
    evaluate_achievements,
    get_runner_status,
    get_sleeping_runners,
    get_user_awards,
)
from app.db import create_database, create_schema
from app.repository import RunInput, add_run


async def _add_run(
    session,
    *,
    message_id: int,
    distance_km: str,
    run_date: date,
) -> None:
    await add_run(
        session,
        RunInput(
            chat_id=-100,
            chat_title="Беговой чат",
            user_id=1,
            username="ivan",
            display_name="Иван",
            telegram_message_id=message_id,
            distance_km=Decimal(distance_km),
            run_date=run_date,
        ),
    )


@pytest.mark.asyncio
async def test_achievements_are_backfilled_and_idempotent() -> None:
    database = create_database("sqlite+aiosqlite:///:memory:")
    await create_schema(database.engine)
    async with database.sessions() as session:
        runs = (
            ("2.1", date(2026, 1, 1)),
            ("5.1", date(2026, 1, 3)),
            ("10", date(2026, 1, 4)),
            ("30", date(2026, 1, 5)),
            ("30", date(2026, 1, 12)),
            ("30", date(2026, 1, 19)),
        )
        for message_id, (distance_km, run_date) in enumerate(runs, start=1):
            await _add_run(
                session,
                message_id=message_id,
                distance_km=distance_km,
                run_date=run_date,
            )

        first = await evaluate_achievements(session, chat_id=-100, user_id=1)
        second = await evaluate_achievements(session, chat_id=-100, user_id=1)
        await session.commit()
        stored = await get_user_awards(session, chat_id=-100, user_id=1)

    codes = {award.code for award in first}
    assert {
        "club_2",
        "club_5",
        "club_10",
        "couch_1",
        "couch_2",
        "couch_3",
        "not_accidental",
        "three_outings",
        "system_4w",
        "total_100",
    } <= codes
    assert second == []
    assert {award.code for award in stored} == codes
    await database.engine.dispose()


@pytest.mark.asyncio
async def test_sleeping_cell_and_comeback_status() -> None:
    database = create_database("sqlite+aiosqlite:///:memory:")
    await create_schema(database.engine)
    async with database.sessions() as session:
        await _add_run(
            session,
            message_id=1,
            distance_km="5",
            run_date=date(2026, 1, 1),
        )
        sleeping = await get_runner_status(
            session,
            chat_id=-100,
            user_id=1,
            today=date(2026, 3, 2),
        )
        sleeping_names = await get_sleeping_runners(
            session,
            chat_id=-100,
            today=date(2026, 3, 2),
        )
        await _add_run(
            session,
            message_id=2,
            distance_km="3",
            run_date=date(2026, 3, 2),
        )
        comeback = await get_runner_status(
            session,
            chat_id=-100,
            user_id=1,
            today=date(2026, 3, 2),
        )

    assert sleeping.title == "Спящая ячейка"
    assert sleeping_names == ["Иван"]
    assert comeback.title == "Снова в эфире"
    await database.engine.dispose()
