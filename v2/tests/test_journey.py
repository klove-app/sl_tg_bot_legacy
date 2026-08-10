from decimal import Decimal
from io import BytesIO

from PIL import Image

from app.journey import (
    build_journey_progress,
    crossed_checkpoints,
    render_journey_map,
)


def test_progress_points_to_next_checkpoint() -> None:
    progress = build_journey_progress(Decimal("874.20"))

    assert progress.percent == Decimal("35.0")
    assert progress.current_checkpoint.code == "black_sea"
    assert progress.next_checkpoint is not None
    assert progress.next_checkpoint.code == "carpathians"
    assert progress.remaining_to_next_km == Decimal("125.80")
    assert progress.remaining_to_finish_km == Decimal("1625.80")


def test_crossing_can_unlock_multiple_checkpoints() -> None:
    crossed = crossed_checkpoints(Decimal("480"), Decimal("1510"))

    assert [checkpoint.code for checkpoint in crossed] == [
        "black_sea",
        "carpathians",
        "danube",
    ]


def test_finish_caps_percent_and_tracks_extra_distance() -> None:
    progress = build_journey_progress(Decimal("2512.40"))

    assert progress.completed is True
    assert progress.percent == Decimal("100.0")
    assert progress.next_checkpoint is None
    assert progress.overage_km == Decimal("12.40")


def test_map_renderer_returns_telegram_ready_png() -> None:
    image_bytes = render_journey_map(build_journey_progress(Decimal("874.20")))
    image = Image.open(BytesIO(image_bytes))

    assert image.format == "PNG"
    assert image.size == (1200, 675)
    assert len(image_bytes) < 10 * 1024 * 1024
