from app.leagues import League, initial_leagues, rollover_leagues


def test_initial_leagues_put_stronger_half_in_tempo() -> None:
    assignments = initial_leagues([1, 2, 3, 4, 5])

    assert assignments == {
        1: League.TEMPO,
        2: League.TEMPO,
        3: League.TEMPO,
        4: League.TRAIL,
        5: League.TRAIL,
    }


def test_rollover_promotes_active_trail_leaders_and_relegates_tempo_tail() -> None:
    assignments = rollover_leagues(
        trail_ordered_user_ids=[4, 5, 6],
        tempo_ordered_user_ids=[1, 2, 3],
        active_trail_user_ids={4, 5},
    )

    assert assignments == {
        1: League.TEMPO,
        2: League.TRAIL,
        3: League.TRAIL,
        4: League.TEMPO,
        5: League.TEMPO,
        6: League.TRAIL,
    }
