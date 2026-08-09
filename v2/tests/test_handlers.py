from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import handlers
from app.db import create_database, create_schema
from app.periods import Period
from app.repository import RunInput, add_run


@pytest.mark.asyncio
async def test_reply_to_bot_without_mention_is_ignored(monkeypatch) -> None:
    save_run = AsyncMock()
    monkeypatch.setattr(handlers, "_save_parsed_run", save_run)
    message = SimpleNamespace(
        chat=SimpleNamespace(type="supergroup"),
        text="Ну тут две у меня, мало ли вдруг больше не будет",
        caption=None,
        reply_to_message=SimpleNamespace(
            from_user=SimpleNamespace(id=123),
        ),
    )

    await handlers.mentioned_run(
        message,
        session=object(),
        settings=object(),
        bot_username="runforestsweaty_bot",
    )

    save_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_mention_is_still_processed(monkeypatch) -> None:
    save_run = AsyncMock()
    monkeypatch.setattr(handlers, "_save_parsed_run", save_run)
    message = SimpleNamespace(
        chat=SimpleNamespace(type="supergroup", id=-100, title="Беговой чат"),
        text="@runforestsweaty_bot 6.03",
        caption=None,
        date=None,
        from_user=None,
        message_id=42,
    )

    await handlers.mentioned_run(
        message,
        session=object(),
        settings=SimpleNamespace(
            allowed_chat_id_set=set(),
            max_distance_km=100,
        ),
        bot_username="runforestsweaty_bot",
    )

    save_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_top_can_show_previous_month_without_zero_rows_in_current_month() -> None:
    database = create_database("sqlite+aiosqlite:///:memory:")
    await create_schema(database.engine)
    async with database.sessions() as session:
        await add_run(
            session,
            RunInput(
                chat_id=-100,
                chat_title="Беговой чат",
                user_id=1,
                username="ksenia",
                display_name="Ксения",
                telegram_message_id=1,
                distance_km=Decimal("5.40"),
                run_date=date(2026, 7, 31),
            ),
        )
        await add_run(
            session,
            RunInput(
                chat_id=-100,
                chat_title="Беговой чат",
                user_id=2,
                username="ivan",
                display_name="Иван",
                telegram_message_id=2,
                distance_km=Decimal("6.00"),
                run_date=date(2026, 8, 2),
            ),
        )
        await session.commit()

        current = await handlers._render_top(
            session,
            chat_id=-100,
            period=Period.MONTH,
            today=date(2026, 8, 9),
        )
        previous = await handlers._render_top(
            session,
            chat_id=-100,
            period=Period.MONTH,
            today=date(2026, 8, 9),
            month_offset=-1,
        )

    assert "Август 2026" in current
    assert "Ксения" not in current
    assert "Июль 2026" in previous
    assert "Ксения" in previous
    assert "5,4 км" in previous
    await database.engine.dispose()
