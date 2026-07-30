from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.config import get_settings
from app.db import create_database, create_schema
from app.repository import RunInput, add_run

LEGACY_QUERY = text(
    """
    SELECT
        running_log.log_id,
        running_log.user_id,
        running_log.km,
        running_log.date_added,
        running_log.notes,
        running_log.chat_id,
        users.username
    FROM running_log
    LEFT JOIN users ON users.user_id = running_log.user_id
    WHERE running_log.chat_id IS NOT NULL
      AND (
          CAST(:chat_id AS TEXT) IS NULL
          OR CAST(running_log.chat_id AS TEXT) = CAST(:chat_id AS TEXT)
      )
    ORDER BY running_log.log_id
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import chat-scoped runs from the legacy schema into v2 tables."
    )
    parser.add_argument("--chat-id", help="Import only one legacy chat ID")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write data. Without this flag the command is a read-only dry run.",
    )
    return parser.parse_args()


async def migrate(*, chat_id: str | None, apply: bool) -> None:
    settings = get_settings()
    database = create_database(settings.database_url)
    try:
        async with database.engine.connect() as connection:
            result = await connection.execute(LEGACY_QUERY, {"chat_id": chat_id})
            rows = result.mappings().all()

        counts = Counter(str(row["chat_id"]) for row in rows)
        print(f"Found {len(rows)} chat-scoped legacy runs across {len(counts)} chats.")
        for source_chat_id, count in counts.most_common():
            print(f"  chat {source_chat_id}: {count} runs")

        if not apply:
            print("Dry run only. Re-run with --apply to write v2 tables.")
            return

        await create_schema(database.engine)
        imported = 0
        skipped = 0
        async with database.sessions() as session:
            for row in rows:
                source_chat_id = int(row["chat_id"])
                source_user_id = int(row["user_id"])
                username = row["username"]
                run_date = row["date_added"]
                if isinstance(run_date, str):
                    run_date = date.fromisoformat(run_date)
                _, created = await add_run(
                    session,
                    RunInput(
                        chat_id=source_chat_id,
                        chat_title=f"Imported chat {source_chat_id}",
                        user_id=source_user_id,
                        username=username,
                        display_name=username or f"Runner {source_user_id}",
                        telegram_message_id=None,
                        distance_km=Decimal(str(row["km"])),
                        run_date=run_date,
                        note=row["notes"],
                        source="legacy",
                        legacy_log_id=int(row["log_id"]),
                    ),
                )
                if created:
                    imported += 1
                else:
                    skipped += 1
            await session.commit()
        print(f"Imported {imported} runs; skipped {skipped} already imported runs.")
    finally:
        await database.engine.dispose()


def main() -> None:
    args = parse_args()
    asyncio.run(migrate(chat_id=args.chat_id, apply=args.apply))


if __name__ == "__main__":
    main()
