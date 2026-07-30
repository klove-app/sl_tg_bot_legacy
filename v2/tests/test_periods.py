from datetime import date

from app.periods import Period, period_range


def test_period_ranges() -> None:
    today = date(2026, 7, 30)

    assert period_range(Period.WEEK, today).start == date(2026, 7, 27)
    assert period_range(Period.MONTH, today).start == date(2026, 7, 1)
    assert period_range(Period.YEAR, today).start == date(2026, 1, 1)
    assert period_range(Period.ALL, today).start is None
    assert period_range(Period.ALL, today).end == today
