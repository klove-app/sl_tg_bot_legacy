from datetime import date
from decimal import Decimal

from app.achievements import ACHIEVEMENT_BY_CODE, AwardView
from app.journey import JOURNEY_CHECKPOINTS, JOURNEY_PLACES, build_journey_progress
from app.leagues import League
from app.periods import Period, period_range
from app.presentation import (
    format_km,
    pluralize,
    render_journey_progress,
    render_league_ranking,
    render_period_summary,
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
        league=League.TRAIL,
        league_place=2,
        league_runners_count=8,
        new_awards=[ACHIEVEMENT_BY_CODE["club_5"]],
        journey_progress=build_journey_progress(Decimal("505.00")),
        new_journey_checkpoints=[JOURNEY_CHECKPOINTS[1]],
    )

    assert "<b>6,03 км</b> · 30 июля" in text
    assert "За месяц: <b>18,43 км</b> · 3 пробежки" in text
    assert "Лига «Тропа»: <b>№2</b> из 8" in text
    assert "🎖 <b>Новые награды</b>" in text
    assert "🔵 Клуб 5 км" in text
    assert "Из Кубани к Монблану" in text
    assert "505 / 2500 км" in text
    assert "Новая точка маршрута" in text
    assert "Сейчас рядом: <b>Tomyna Balka</b>" in text
    assert "Большая остановка: <b>Керчь</b>" in text
    assert "более 2 600 лет" in text
    assert "/journey · 🏆 /top · 👤 /me · ↩️ /undo" in text
    assert len(text) <= 1024


def test_new_travel_stop_is_announced_with_its_fact_once() -> None:
    place = JOURNEY_PLACES[4]
    text = render_journey_progress(
        build_journey_progress(Decimal("830.00")),
        newly_reached_places=[place],
    )

    assert "Новая остановка на маршруте" in text
    assert "<b>Бутучены · Старый Орхей</b>" in text
    assert text.count(place.fact) == 1


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


def test_render_league_ranking_has_both_leagues() -> None:
    entry = RankingEntry(
        user_id=1,
        display_name="Иван",
        username="ivan",
        total_km=Decimal("25.40"),
        runs_count=4,
        best_run_km=Decimal("10.00"),
    )
    text = render_league_ranking(
        period=Period.WEEK,
        rankings={League.TEMPO: [entry], League.TRAIL: []},
        totals=Totals(total_km=Decimal("25.40"), runs_count=4, runners_count=1),
    )

    assert "Беговой рейтинг · Неделя" in text
    assert "Лига «Темп»" in text
    assert "Лига «Тропа»" in text


def test_render_monthly_summary_lists_all_leagues_and_totals() -> None:
    entry = RankingEntry(
        user_id=1,
        display_name="Иван",
        username="ivan",
        total_km=Decimal("25.40"),
        runs_count=4,
        best_run_km=Decimal("10.00"),
    )
    text = render_period_summary(
        period=Period.MONTH,
        date_range=period_range(Period.MONTH, date(2026, 8, 31)),
        rankings={League.TEMPO: [entry], League.TRAIL: []},
        totals=Totals(total_km=Decimal("25.40"), runs_count=4, runners_count=1),
        awards=[
            AwardView(
                user_id=1,
                display_name="Иван",
                definition=ACHIEVEMENT_BY_CODE["not_accidental"],
                reference_date=date(2026, 8, 10),
            )
        ],
        sleeping_runners=["Ксения & друзья"],
    )

    assert "<b>Итоги месяца</b> · 1–31 августа" in text
    assert "25,4 км</b> вместе" in text
    assert "👟 <b>Иван</b> — Это уже не случайность" in text
    assert "🔥 Держит Темп — <b>Иван</b>" in text
    assert "Спящие ячейки:</b> Ксения &amp; друзья" in text
    assert "переходят в «Темп»" in text
