from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from app.db import create_database, create_schema
from app.leagues import League
from app.periods import Period, period_range
from app.repository import (
    RunInput,
    add_run,
    backfill_journey_milestones,
    claim_journey_milestones,
    ensure_month_leagues,
    get_journey_totals,
    get_league_ranking,
    get_ranking,
    get_totals,
    get_user_stats,
    soft_delete_owned_run,
)


@pytest_asyncio.fixture
async def database():
    database = create_database("sqlite+aiosqlite:///:memory:")
    await create_schema(database.engine)
    async with database.engine.begin() as connection:
        await connection.exec_driver_sql("PRAGMA foreign_keys=ON")
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
async def test_first_run_creates_foreign_key_parents_before_run(database) -> None:
    async with database.sessions() as session:
        run, created = await add_run(
            session,
            run_input(
                chat_id=-1001487049035,
                user_id=1431390352,
                message_id=1,
                distance="6.03",
            ),
        )
        await session.commit()

    assert created is True
    assert run.distance_km == Decimal("6.03")


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


@pytest.mark.asyncio
async def test_journey_totals_and_milestones_are_isolated_and_idempotent(database) -> None:
    async with database.sessions() as session:
        first, _ = await add_run(
            session,
            run_input(chat_id=1, user_id=10, message_id=1, distance="490.00"),
        )
        second, _ = await add_run(
            session,
            run_input(chat_id=1, user_id=10, message_id=2, distance="15.00"),
        )
        await add_run(
            session,
            run_input(chat_id=2, user_id=10, message_id=1, distance="900.00"),
        )
        await add_run(
            session,
            run_input(
                chat_id=1,
                user_id=10,
                message_id=3,
                distance="300.00",
                run_date=date(2025, 12, 31),
            ),
        )
        totals = await get_journey_totals(
            session,
            chat_id=1,
            through=date(2026, 12, 31),
        )
        first_claim = await claim_journey_milestones(
            session,
            chat_id=1,
            checkpoint_codes=["black_sea"],
            reached_total_km=totals.total_km,
            run_id=second.id,
        )
        duplicate_claim = await claim_journey_milestones(
            session,
            chat_id=1,
            checkpoint_codes=["black_sea"],
            reached_total_km=totals.total_km,
            run_id=second.id,
        )
        await soft_delete_owned_run(
            session,
            run_id=second.id,
            chat_id=1,
            user_id=10,
        )
        await session.commit()
        after_undo = await get_journey_totals(
            session,
            chat_id=1,
            through=date(2026, 12, 31),
        )

    assert first.id is not None
    assert totals.total_km == Decimal("505.00")
    assert first_claim == ["black_sea"]
    assert duplicate_claim == []
    assert after_undo.total_km == Decimal("490.00")


@pytest.mark.asyncio
async def test_journey_backfill_silently_reserves_old_checkpoints(database) -> None:
    async with database.sessions() as session:
        run, _ = await add_run(
            session,
            run_input(chat_id=1, user_id=10, message_id=1, distance="600.00"),
        )
        await session.commit()

    await backfill_journey_milestones(database.sessions)

    async with database.sessions() as session:
        repeated = await claim_journey_milestones(
            session,
            chat_id=1,
            checkpoint_codes=["black_sea"],
            reached_total_km=Decimal("600.00"),
            run_id=run.id,
        )

    assert repeated == []


@pytest.mark.asyncio
async def test_month_leagues_are_seeded_and_ranked_independently(database) -> None:
    async with database.sessions() as session:
        for user_id, distance in [(10, "30.00"), (20, "20.00"), (30, "10.00"), (40, "5.00")]:
            await add_run(
                session,
                run_input(
                    chat_id=1,
                    user_id=user_id,
                    message_id=user_id,
                    distance=distance,
                    run_date=date(2026, 8, 9),
                ),
            )

        assignments = await ensure_month_leagues(
            session,
            chat_id=1,
            membership_month=date(2026, 8, 1),
            seed_end=date(2026, 8, 9),
        )
        tempo = await get_league_ranking(
            session,
            chat_id=1,
            membership_month=date(2026, 8, 1),
            league=League.TEMPO,
            date_range=period_range(Period.MONTH, date(2026, 8, 9)),
        )
        trail = await get_league_ranking(
            session,
            chat_id=1,
            membership_month=date(2026, 8, 1),
            league=League.TRAIL,
            date_range=period_range(Period.MONTH, date(2026, 8, 9)),
        )

    assert assignments == {
        10: League.TEMPO,
        20: League.TEMPO,
        30: League.TRAIL,
        40: League.TRAIL,
    }
    assert [entry.user_id for entry in tempo] == [10, 20]
    assert [entry.user_id for entry in trail] == [30, 40]
