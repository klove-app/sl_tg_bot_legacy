from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

JOURNEY_YEAR = 2026
JOURNEY_TITLE = "Из Кубани к Монблану"
JOURNEY_TARGET_KM = Decimal("2500")
MAP_SIZE = (1200, 675)
MAP_ASSET_PATH = Path(__file__).with_name("assets") / "journey-map-base.png"


@dataclass(frozen=True)
class JourneyCheckpoint:
    code: str
    distance_km: Decimal
    title: str
    map_label: str
    point: tuple[int, int]


@dataclass(frozen=True)
class JourneyProgress:
    total_km: Decimal
    target_km: Decimal
    percent: Decimal
    current_checkpoint: JourneyCheckpoint
    next_checkpoint: JourneyCheckpoint | None
    remaining_to_next_km: Decimal
    remaining_to_finish_km: Decimal
    overage_km: Decimal

    @property
    def completed(self) -> bool:
        return self.total_km >= self.target_km


JOURNEY_CHECKPOINTS = (
    JourneyCheckpoint(
        code="krasnodar",
        distance_km=Decimal("0"),
        title="Парк Краснодар",
        map_label="KRASNODAR",
        point=(1162, 345),
    ),
    JourneyCheckpoint(
        code="black_sea",
        distance_km=Decimal("500"),
        title="Чёрное море",
        map_label="BLACK SEA",
        point=(973, 350),
    ),
    JourneyCheckpoint(
        code="carpathians",
        distance_km=Decimal("1000"),
        title="Карпаты",
        map_label="CARPATHIANS",
        point=(670, 330),
    ),
    JourneyCheckpoint(
        code="danube",
        distance_km=Decimal("1500"),
        title="Дунай",
        map_label="DANUBE",
        point=(490, 300),
    ),
    JourneyCheckpoint(
        code="alps",
        distance_km=Decimal("2000"),
        title="Альпы",
        map_label="ALPS",
        point=(270, 330),
    ),
    JourneyCheckpoint(
        code="chamonix",
        distance_km=JOURNEY_TARGET_KM,
        title="Шамони · Монблан",
        map_label="CHAMONIX",
        point=(90, 326),
    ),
)

ROUTE_TRACK = (
    (Decimal("0"), (1162, 345)),
    (Decimal("125"), (1125, 340)),
    (Decimal("250"), (1080, 344)),
    (Decimal("375"), (1030, 340)),
    (Decimal("500"), (973, 350)),
    (Decimal("625"), (910, 365)),
    (Decimal("750"), (845, 355)),
    (Decimal("875"), (770, 345)),
    (Decimal("1000"), (670, 330)),
    (Decimal("1125"), (620, 327)),
    (Decimal("1250"), (575, 315)),
    (Decimal("1375"), (535, 310)),
    (Decimal("1500"), (490, 300)),
    (Decimal("1625"), (440, 303)),
    (Decimal("1750"), (385, 320)),
    (Decimal("1875"), (330, 317)),
    (Decimal("2000"), (270, 330)),
    (Decimal("2125"), (220, 337)),
    (Decimal("2250"), (170, 325)),
    (Decimal("2375"), (125, 330)),
    (JOURNEY_TARGET_KM, (90, 326)),
)


def build_journey_progress(total_km: Decimal) -> JourneyProgress:
    total = max(Decimal("0"), Decimal(total_km)).quantize(Decimal("0.01"))
    capped = min(total, JOURNEY_TARGET_KM)
    percent = (capped / JOURNEY_TARGET_KM * 100).quantize(Decimal("0.1"))
    current = JOURNEY_CHECKPOINTS[0]
    next_checkpoint: JourneyCheckpoint | None = None
    for checkpoint in JOURNEY_CHECKPOINTS:
        if checkpoint.distance_km <= total:
            current = checkpoint
            continue
        next_checkpoint = checkpoint
        break

    remaining_to_next = (
        max(Decimal("0"), next_checkpoint.distance_km - total)
        if next_checkpoint is not None
        else Decimal("0")
    )
    return JourneyProgress(
        total_km=total,
        target_km=JOURNEY_TARGET_KM,
        percent=percent,
        current_checkpoint=current,
        next_checkpoint=next_checkpoint,
        remaining_to_next_km=remaining_to_next.quantize(Decimal("0.01")),
        remaining_to_finish_km=max(Decimal("0"), JOURNEY_TARGET_KM - total).quantize(
            Decimal("0.01")
        ),
        overage_km=max(Decimal("0"), total - JOURNEY_TARGET_KM).quantize(
            Decimal("0.01")
        ),
    )


def crossed_checkpoints(
    previous_total_km: Decimal,
    current_total_km: Decimal,
) -> tuple[JourneyCheckpoint, ...]:
    previous = Decimal(previous_total_km)
    current = Decimal(current_total_km)
    if current <= previous:
        return ()
    return tuple(
        checkpoint
        for checkpoint in JOURNEY_CHECKPOINTS[1:]
        if previous < checkpoint.distance_km <= current
    )


def checkpoint_by_code(code: str) -> JourneyCheckpoint:
    return next(checkpoint for checkpoint in JOURNEY_CHECKPOINTS if checkpoint.code == code)


def _font(size: int):
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=1)
def _base_map() -> Image.Image:
    with Image.open(MAP_ASSET_PATH) as source:
        return ImageOps.fit(
            source.convert("RGB"),
            MAP_SIZE,
            method=Image.Resampling.LANCZOS,
        )


def _point_at_progress(progress: JourneyProgress) -> tuple[int, int]:
    distance = min(progress.total_km, progress.target_km)
    if distance >= progress.target_km:
        return ROUTE_TRACK[-1][1]
    for start, end in zip(ROUTE_TRACK, ROUTE_TRACK[1:], strict=False):
        start_distance, start_point = start
        end_distance, end_point = end
        if distance <= end_distance:
            span = end_distance - start_distance
            ratio = float((distance - start_distance) / span)
            return (
                round(start_point[0] + (end_point[0] - start_point[0]) * ratio),
                round(start_point[1] + (end_point[1] - start_point[1]) * ratio),
            )
    return ROUTE_TRACK[-1][1]


def _travelled_polyline(progress: JourneyProgress) -> list[tuple[int, int]]:
    distance = min(progress.total_km, progress.target_km)
    points = [ROUTE_TRACK[0][1]]
    for track_distance, point in ROUTE_TRACK[1:]:
        if track_distance <= distance:
            points.append(point)
        else:
            points.append(_point_at_progress(progress))
            break
    return points


def render_journey_map(progress: JourneyProgress) -> bytes:
    image = _base_map().copy().convert("RGBA")
    overlay = Image.new("RGBA", MAP_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    route_points = [point for _, point in ROUTE_TRACK]
    draw.line(route_points, fill=(3, 8, 8, 190), width=13, joint="curve")
    draw.line(route_points, fill=(190, 195, 191, 255), width=7, joint="curve")
    travelled = _travelled_polyline(progress)
    if len(travelled) > 1:
        draw.line(travelled, fill=(3, 8, 8, 190), width=14, joint="curve")
        draw.line(travelled, fill=(255, 95, 69, 255), width=8, joint="curve")

    for checkpoint in JOURNEY_CHECKPOINTS:
        x, y = checkpoint.point
        reached = checkpoint.distance_km <= progress.total_km
        fill = (255, 95, 69, 255) if reached else (205, 210, 207, 255)
        draw.ellipse(
            (x - 8, y - 8, x + 8, y + 8),
            fill=fill,
            outline=(248, 245, 235, 255),
            width=4,
        )

    marker_x, marker_y = _point_at_progress(progress)
    draw.ellipse(
        (marker_x - 17, marker_y - 17, marker_x + 17, marker_y + 17),
        fill=(255, 95, 69, 255),
        outline=(255, 250, 239, 255),
        width=6,
    )

    draw.rounded_rectangle(
        (28, 25, 430, 105),
        radius=20,
        fill=(3, 10, 10, 205),
        outline=(255, 255, 255, 35),
        width=1,
    )
    draw.text((50, 42), "KUBAN TO MONT BLANC", font=_font(26), fill="#f8f5eb")
    draw.text((50, 75), "2,500 KM TOGETHER / 2026", font=_font(15), fill="#bac5bf")

    draw.rounded_rectangle(
        (28, 575, 1172, 650),
        radius=22,
        fill=(3, 10, 10, 215),
        outline=(255, 255, 255, 35),
        width=1,
    )
    bar_left, bar_top, bar_right, bar_bottom = 50, 598, 935, 617
    draw.rounded_rectangle(
        (bar_left, bar_top, bar_right, bar_bottom),
        radius=10,
        fill=(83, 92, 88, 235),
    )
    ratio = min(1.0, float(progress.total_km / progress.target_km))
    fill_right = bar_left + round((bar_right - bar_left) * ratio)
    if fill_right > bar_left:
        draw.rounded_rectangle(
            (bar_left, bar_top, fill_right, bar_bottom),
            radius=10,
            fill=(255, 95, 69, 255),
        )
    draw.text(
        (50, 624),
        f"{progress.total_km:.1f} / {progress.target_km:.0f} KM",
        font=_font(17),
        fill="#f8f5eb",
    )
    draw.text(
        (1025, 601),
        f"{progress.percent:.1f}%",
        font=_font(23),
        fill="#ff735c",
    )

    image = Image.alpha_composite(image, overlay).convert("RGB")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
