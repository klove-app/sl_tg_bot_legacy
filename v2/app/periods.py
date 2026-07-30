from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class Period(StrEnum):
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"


@dataclass(frozen=True)
class DateRange:
    start: date | None
    end: date


def period_range(period: Period, today: date) -> DateRange:
    if period is Period.WEEK:
        return DateRange(start=today - timedelta(days=today.weekday()), end=today)
    if period is Period.MONTH:
        return DateRange(start=today.replace(day=1), end=today)
    if period is Period.YEAR:
        return DateRange(start=today.replace(month=1, day=1), end=today)
    return DateRange(start=None, end=today)


def period_label(period: Period) -> str:
    return {
        Period.WEEK: "эту неделю",
        Period.MONTH: "этот месяц",
        Period.YEAR: "этот год",
        Period.ALL: "всё время",
    }[period]
