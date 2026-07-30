from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: SecretStr | None = Field(
        default=None,
        alias="TELEGRAM_BOT_TOKEN",
    )
    database_url: str = Field(alias="DATABASE_URL")
    bot_timezone: str = Field(default="Europe/Moscow", alias="BOT_TIMEZONE")
    max_distance_km: Decimal = Field(default=Decimal("100"), alias="MAX_DISTANCE_KM")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    allowed_chat_ids: str | None = Field(default=None, alias="ALLOWED_CHAT_IDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.strip()
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("bot_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown timezone: {value}") from exc
        return value

    @field_validator("max_distance_km")
    @classmethod
    def validate_max_distance(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("MAX_DISTANCE_KM must be positive")
        return value

    @property
    def allowed_chat_id_set(self) -> set[int]:
        if not self.allowed_chat_ids:
            return set()
        return {
            int(item.strip())
            for item in self.allowed_chat_ids.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
