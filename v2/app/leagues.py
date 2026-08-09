from __future__ import annotations

from enum import StrEnum


class League(StrEnum):
    TRAIL = "trail"
    TEMPO = "tempo"


LEAGUE_TITLES = {
    League.TRAIL: "Тропа",
    League.TEMPO: "Темп",
}

LEAGUE_EMOJI = {
    League.TRAIL: "🌱",
    League.TEMPO: "🔥",
}


def initial_leagues(ordered_user_ids: list[int]) -> dict[int, League]:
    """Seed roughly the strongest 40% into Tempo and everyone else into Trail."""
    runners_count = len(ordered_user_ids)
    if runners_count < 2:
        return {user_id: League.TRAIL for user_id in ordered_user_ids}

    tempo_count = max(1, round(runners_count * 0.4))
    tempo_count = min(tempo_count, runners_count - 1)
    return {
        user_id: League.TEMPO if index < tempo_count else League.TRAIL
        for index, user_id in enumerate(ordered_user_ids)
    }


def rollover_leagues(
    *,
    trail_ordered_user_ids: list[int],
    tempo_ordered_user_ids: list[int],
    active_trail_user_ids: set[int],
) -> dict[int, League]:
    """Promote up to two active Trail leaders and relegate the same number."""
    all_user_ids = tempo_ordered_user_ids + trail_ordered_user_ids
    if not tempo_ordered_user_ids or not trail_ordered_user_ids:
        return initial_leagues(all_user_ids)

    promotion_candidates = [
        user_id
        for user_id in trail_ordered_user_ids
        if user_id in active_trail_user_ids
    ]
    move_count = min(
        2,
        len(promotion_candidates),
        max(0, len(tempo_ordered_user_ids) - 1),
    )
    promoted = set(promotion_candidates[:move_count])
    relegated = set(tempo_ordered_user_ids[-move_count:]) if move_count else set()

    assignments: dict[int, League] = {}
    for user_id in tempo_ordered_user_ids:
        assignments[user_id] = League.TRAIL if user_id in relegated else League.TEMPO
    for user_id in trail_ordered_user_ids:
        assignments[user_id] = League.TEMPO if user_id in promoted else League.TRAIL
    return assignments
