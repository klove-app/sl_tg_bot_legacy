from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import handlers


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
