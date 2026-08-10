from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

JOURNEY_YEAR = 2026
JOURNEY_TITLE = "Из Кубани к Монблану"
JOURNEY_TARGET_KM = Decimal("2500")


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
        point=(1050, 405),
    ),
    JourneyCheckpoint(
        code="black_sea",
        distance_km=Decimal("500"),
        title="Чёрное море",
        map_label="BLACK SEA",
        point=(890, 440),
    ),
    JourneyCheckpoint(
        code="carpathians",
        distance_km=Decimal("1000"),
        title="Карпаты",
        map_label="CARPATHIANS",
        point=(690, 300),
    ),
    JourneyCheckpoint(
        code="danube",
        distance_km=Decimal("1500"),
        title="Дунай",
        map_label="DANUBE",
        point=(505, 345),
    ),
    JourneyCheckpoint(
        code="alps",
        distance_km=Decimal("2000"),
        title="Альпы",
        map_label="ALPS",
        point=(315, 260),
    ),
    JourneyCheckpoint(
        code="chamonix",
        distance_km=JOURNEY_TARGET_KM,
        title="Шамони · Монблан",
        map_label="CHAMONIX",
        point=(155, 365),
    ),
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


def _point_at_progress(progress: JourneyProgress) -> tuple[int, int]:
    distance = min(progress.total_km, progress.target_km)
    if distance >= progress.target_km:
        return JOURNEY_CHECKPOINTS[-1].point
    for start, end in zip(JOURNEY_CHECKPOINTS, JOURNEY_CHECKPOINTS[1:], strict=False):
        if distance <= end.distance_km:
            span = end.distance_km - start.distance_km
            ratio = float((distance - start.distance_km) / span)
            return (
                round(start.point[0] + (end.point[0] - start.point[0]) * ratio),
                round(start.point[1] + (end.point[1] - start.point[1]) * ratio),
            )
    return JOURNEY_CHECKPOINTS[-1].point


def _travelled_polyline(progress: JourneyProgress) -> list[tuple[int, int]]:
    distance = min(progress.total_km, progress.target_km)
    points = [JOURNEY_CHECKPOINTS[0].point]
    for checkpoint in JOURNEY_CHECKPOINTS[1:]:
        if checkpoint.distance_km <= distance:
            points.append(checkpoint.point)
        else:
            points.append(_point_at_progress(progress))
            break
    return points


def render_journey_map(progress: JourneyProgress) -> bytes:
    image = Image.new("RGB", (1200, 675), "#081b1a")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((35, 28, 1165, 647), radius=32, fill="#102a27")
    draw.text((75, 62), "KUBAN TO MONT BLANC", font=_font(36), fill="#f5f1df")
    draw.text(
        (75, 108),
        "2,500 KM TOGETHER / 2026",
        font=_font(20),
        fill="#8fd3b1",
    )

    map_box = (70, 165, 1130, 505)
    draw.rounded_rectangle(map_box, radius=26, fill="#153b35", outline="#2b5b50", width=2)
    for x in range(160, 1130, 145):
        draw.line((x, 185, x - 65, 485), fill="#1e4942", width=1)
    for y in range(215, 490, 65):
        draw.line((90, y, 1110, y - 18), fill="#1e4942", width=1)

    draw.ellipse((780, 300, 1060, 520), fill="#123d46", outline="#267080", width=2)
    draw.polygon(
        [(75, 430), (220, 285), (320, 365), (405, 230), (540, 405), (75, 505)],
        fill="#1b463c",
    )
    draw.polygon(
        [(90, 445), (220, 315), (275, 382), (405, 255), (505, 415)],
        fill="#2e6250",
    )

    route_points = [checkpoint.point for checkpoint in JOURNEY_CHECKPOINTS]
    draw.line(route_points, fill="#6d8078", width=10, joint="curve")
    travelled = _travelled_polyline(progress)
    if len(travelled) > 1:
        draw.line(travelled, fill="#66e29c", width=12, joint="curve")

    for index, checkpoint in enumerate(JOURNEY_CHECKPOINTS):
        x, y = checkpoint.point
        reached = checkpoint.distance_km <= progress.total_km
        fill = "#66e29c" if reached else "#d5ddcf"
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=fill, outline="#081b1a", width=3)
        label_y = y - 47 if index % 2 == 0 else y + 20
        draw.text((x - 44, label_y), checkpoint.map_label, font=_font(14), fill="#f5f1df")
        draw.text(
            (x - 26, label_y + 17),
            f"{int(checkpoint.distance_km)} KM",
            font=_font(12),
            fill="#9db4aa",
        )

    marker_x, marker_y = _point_at_progress(progress)
    draw.ellipse(
        (marker_x - 19, marker_y - 19, marker_x + 19, marker_y + 19),
        fill="#ffca58",
        outline="#fff3c4",
        width=5,
    )

    bar_left, bar_top, bar_right, bar_bottom = 75, 555, 1125, 588
    draw.rounded_rectangle(
        (bar_left, bar_top, bar_right, bar_bottom),
        radius=16,
        fill="#29423d",
    )
    ratio = min(1.0, float(progress.total_km / progress.target_km))
    fill_right = bar_left + round((bar_right - bar_left) * ratio)
    if fill_right > bar_left:
        draw.rounded_rectangle(
            (bar_left, bar_top, fill_right, bar_bottom),
            radius=16,
            fill="#66e29c",
        )
    draw.text(
        (75, 603),
        f"{progress.total_km:.1f} / {progress.target_km:.0f} KM",
        font=_font(22),
        fill="#f5f1df",
    )
    draw.text(
        (1020, 603),
        f"{progress.percent:.1f}%",
        font=_font(22),
        fill="#ffca58",
    )

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
