from decimal import Decimal

import pytest

from app.parsing import RunParseError, parse_run_text


@pytest.mark.parametrize(
    ("text", "distance", "note"),
    [
        ("/run 5.2", Decimal("5.20"), None),
        ("/run 5,25 утренний парк", Decimal("5.25"), "утренний парк"),
        ("/run@club_bot сегодня 10 км легко", Decimal("10.00"), "сегодня легко"),
        ("@club_bot 7.5 km tempo", Decimal("7.50"), "@club_bot tempo"),
    ],
)
def test_parse_distance(text: str, distance: Decimal, note: str | None) -> None:
    parsed = parse_run_text(
        text,
        max_distance_km=Decimal("100"),
        require_command=text.startswith("/"),
    )
    assert parsed.distance_km == distance
    assert parsed.note == note


@pytest.mark.parametrize("text", ["/run", "/run 0", "/run 100.01", "5.2"])
def test_rejects_invalid_command(text: str) -> None:
    with pytest.raises(RunParseError):
        parse_run_text(
            text,
            max_distance_km=Decimal("100"),
            require_command=True,
        )
