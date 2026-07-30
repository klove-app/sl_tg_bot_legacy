from datetime import date
from decimal import Decimal

from app.periods import Period
from app.presentation import (
    format_km,
    pluralize,
    render_ranking,
    render_run_confirmation,
)
from app.repository import RankingEntry, Totals, UserStats


def test_format_km_uses_compact_russian_decimal() -> None:
    assert format_km(Decimal("6.03")) == "6,03"
    assert format_km(Decimal("10.00")) == "10"


def test_pluralize_russian_runs() -> None:
    assert pluralize(1, "пробежка", "пробежки", "пробежек") == "1 пробежка"
    assert pluralize(3, "пробежка", "пробежки", "пробежек") == "3 пробежки"
    assert pluralize(12, "пробежка", "пробежки", "пробежек") == "12 пробежек"


def test_render_run_confirmation_contains_stats_rank_and_commands() -> None:
    text = render_run_confirmation(
        distance_km=Decimal("6.03"),
        run_date=date(2026, 7, 30),
        note="утренний парк",
        month_stats=UserStats(
            total_km=Decimal("18.43"),
            runs_count=3,
            best_run_km=Decimal("8.20"),
        ),
        month_place=2,
        runners_count=8,
    )

    assert "<b>6,03 км</b> · 30 июля" in text
    assert "За месяц: <b>18,43 км</b> · 3 пробежки" in text
    assert "№2" in text
    assert "/top · 👤 /me · ↩️ /undo" in text


def test_render_ranking_has_clean_rows_and_totals() -> None:
    text = render_ranking(
        period=Period.MONTH,
        ranking=[
            RankingEntry(
                user_id=1,
                display_name="Иван & друзья",
                username="ivan",
                total_km=Decimal("25.40"),
                runs_count=4,
                best_run_km=Decimal("10.00"),
            )
        ],
        totals=Totals(
            total_km=Decimal("25.40"),
            runs_count=4,
            runners_count=1,
        ),
    )

    assert "🏆 <b>Рейтинг · Месяц</b>" in text
    assert "🥇 <b>Иван &amp; друзья</b> — <b>25,4 км</b> · 4 пробежки" in text
    assert "👟 1 участник · 4 пробежки" in text
    assert "🛣 Вместе: <b>25,4 км</b>" in text
