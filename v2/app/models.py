from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


RUN_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")
DISTANCE_TYPE = Numeric(7, 2).with_variant(Float(asdecimal=True), "sqlite")


class Chat(Base):
    __tablename__ = "runbot_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class Runner(Base):
    __tablename__ = "runbot_runners"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id"],
            ["runbot_chats.chat_id"],
            ondelete="CASCADE",
        ),
    )


class Run(Base):
    __tablename__ = "runbot_runs"

    id: Mapped[int] = mapped_column(RUN_ID_TYPE, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    distance_km: Mapped[Decimal] = mapped_column(DISTANCE_TYPE, nullable=False)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="telegram")
    legacy_log_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "user_id"],
            ["runbot_runners.chat_id", "runbot_runners.user_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "chat_id",
            "telegram_message_id",
            name="uq_runbot_runs_chat_message",
        ),
        UniqueConstraint("legacy_log_id", name="uq_runbot_runs_legacy_log"),
        Index(
            "ix_runbot_runs_chat_date_active",
            "chat_id",
            "run_date",
            "deleted_at",
        ),
        Index(
            "ix_runbot_runs_chat_user_date",
            "chat_id",
            "user_id",
            "run_date",
        ),
    )


class LeagueMembership(Base):
    __tablename__ = "runbot_league_memberships"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    month_start: Mapped[date] = mapped_column(Date, primary_key=True)
    league: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "user_id"],
            ["runbot_runners.chat_id", "runbot_runners.user_id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_runbot_league_memberships_chat_month_league",
            "chat_id",
            "month_start",
            "league",
        ),
    )


class SummaryDelivery(Base):
    __tablename__ = "runbot_summary_deliveries"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    summary_kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    period_start: Mapped[date] = mapped_column(Date, primary_key=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id"],
            ["runbot_chats.chat_id"],
            ondelete="CASCADE",
        ),
    )


class AchievementAward(Base):
    __tablename__ = "runbot_achievement_awards"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    period_key: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default="lifetime",
    )
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id", "user_id"],
            ["runbot_runners.chat_id", "runbot_runners.user_id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_runbot_achievement_awards_chat_date",
            "chat_id",
            "reference_date",
        ),
    )


class JourneyMilestone(Base):
    __tablename__ = "runbot_journey_milestones"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    checkpoint_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    reached_total_km: Mapped[Decimal] = mapped_column(DISTANCE_TYPE, nullable=False)
    run_id: Mapped[int | None] = mapped_column(RUN_ID_TYPE, nullable=True)
    reached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        ForeignKeyConstraint(
            ["chat_id"],
            ["runbot_chats.chat_id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_runbot_journey_milestones_chat_year",
            "chat_id",
            "year",
        ),
    )
