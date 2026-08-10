from decimal import Decimal
from io import BytesIO

from PIL import Image

from app.journey import (
    JOURNEY_WAYPOINTS,
    build_journey_progress,
    crossed_checkpoints,
    crossed_places,
    render_journey_map,
)


def test_progress_points_to_next_checkpoint() -> None:
    progress = build_journey_progress(Decimal("874.20"))

    assert progress.percent == Decimal("35.0")
    assert progress.current_checkpoint.code == "black_sea"
    assert progress.next_checkpoint is not None
    assert progress.next_checkpoint.code == "carpathians"
    assert progress.remaining_to_next_km == Decimal("210.40")
    assert progress.remaining_to_finish_km == Decimal("1625.80")
    assert progress.current_place.code == "butuceni"
    assert progress.next_place is not None
    assert progress.next_place.code == "viscri"
    assert progress.remaining_to_next_place_km == Decimal("210.40")
    assert progress.current_waypoint.distance_km == Decimal("862.5")
    assert progress.current_waypoint.title == "Urșița"
    assert progress.next_waypoint is not None
    assert progress.next_waypoint.distance_km == Decimal("875.0")
    assert progress.remaining_to_next_waypoint_km == Decimal("0.80")


def test_dense_waypoints_update_location_every_twelve_and_a_half_km() -> None:
    distances = [waypoint.distance_km for waypoint in JOURNEY_WAYPOINTS]
    gaps = [end - start for start, end in zip(distances, distances[1:], strict=False)]
    progress = build_journey_progress(Decimal("163.00"))

    assert len(JOURNEY_WAYPOINTS) == 201
    assert set(gaps) == {Decimal("12.5")}
    assert max(waypoint.place_offset_km for waypoint in JOURNEY_WAYPOINTS) <= Decimal(
        "16"
    )
    assert progress.current_waypoint.distance_km == Decimal("162.5")
    assert progress.current_waypoint.title == "Глазовка"
    assert progress.current_place.code == "taman"
    assert progress.next_waypoint is not None
    assert progress.next_waypoint.distance_km == Decimal("175.0")
    assert progress.remaining_to_next_waypoint_km == Decimal("12.00")


def test_crossing_can_unlock_multiple_checkpoints() -> None:
    crossed = crossed_checkpoints(Decimal("160"), Decimal("1600"))

    assert [checkpoint.code for checkpoint in crossed] == [
        "black_sea",
        "carpathians",
        "danube",
    ]


def test_crossing_unlocks_curated_travel_stops() -> None:
    crossed = crossed_places(Decimal("140"), Decimal("840"))

    assert [place.code for place in crossed] == [
        "taman",
        "kerch",
        "nerubayske",
        "butuceni",
    ]


def test_finish_caps_percent_and_tracks_extra_distance() -> None:
    progress = build_journey_progress(Decimal("2512.40"))

    assert progress.completed is True
    assert progress.percent == Decimal("100.0")
    assert progress.next_checkpoint is None
    assert progress.overage_km == Decimal("12.40")
    assert progress.current_place.code == "chamonix"
    assert progress.next_place is None


def test_map_renderer_returns_telegram_ready_png() -> None:
    image_bytes = render_journey_map(build_journey_progress(Decimal("874.20")))
    image = Image.open(BytesIO(image_bytes))

    assert image.format == "PNG"
    assert image.size == (1200, 675)
    assert len(image_bytes) < 10 * 1024 * 1024
