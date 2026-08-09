from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class Period(StrEnum):
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"


MONTH_NAMES_NOMINATIVE = (
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
)


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


def month_start(value: date) -> date:
    return value.replace(day=1)


def previous_month_start(value: date) -> date:
    return (month_start(value) - timedelta(days=1)).replace(day=1)


def month_date_range(value: date) -> DateRange:
    start = month_start(value)
    end = start.replace(day=calendar.monthrange(start.year, start.month)[1])
    return DateRange(start=start, end=end)


def week_date_range(value: date) -> DateRange:
    start = value - timedelta(days=value.weekday())
    return DateRange(start=start, end=start + timedelta(days=6))
