from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.models import Base


@dataclass(frozen=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def create_database(database_url: str) -> Database:
    options: dict[str, object] = {
        "pool_pre_ping": True,
    }
    if database_url.startswith("sqlite+aiosqlite:///:memory:"):
        options["poolclass"] = StaticPool
        options["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(database_url, **options)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return Database(engine=engine, sessions=sessions)


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
