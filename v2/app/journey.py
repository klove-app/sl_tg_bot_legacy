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
MAP_ASSET_PATH = Path(__file__).with_name("assets") / "journey-map-cartoon.png"

INK = (45, 52, 61, 255)
CREAM = (255, 249, 225, 242)
CORAL = (244, 91, 91, 255)
SUN = (255, 194, 72, 255)
MINT = (55, 166, 145, 255)
LAVENDER = (114, 91, 169, 255)


@dataclass(frozen=True)
class JourneyCheckpoint:
    code: str
    distance_km: Decimal
    title: str
    map_label: str
    point: tuple[int, int]


@dataclass(frozen=True)
class JourneyPlace:
    code: str
    distance_km: Decimal
    title: str
    map_label: str
    fact: str


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
    current_place: JourneyPlace
    next_place: JourneyPlace | None
    remaining_to_next_place_km: Decimal

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

JOURNEY_PLACES = (
    JourneyPlace(
        code="krasnodar_park",
        distance_km=Decimal("0"),
        title="Парк Краснодар",
        map_label="PARK KRASNODAR",
        fact="Здесь начинается наш общий путь длиной 2 500 км.",
    ),
    JourneyPlace(
        code="taman",
        distance_km=Decimal("200"),
        title="Тамань",
        map_label="TAMAN",
        fact="Таманский полуостров лежит между Азовским и Чёрным морями.",
    ),
    JourneyPlace(
        code="kerch",
        distance_km=Decimal("400"),
        title="Керчь",
        map_label="KERCH",
        fact="История города насчитывает более 2 600 лет; античный центр назывался Пантикапей.",
    ),
    JourneyPlace(
        code="nerubayske",
        distance_km=Decimal("625"),
        title="Нерубайское",
        map_label="NERUBAYSKE",
        fact=(
            "Рядом начинается часть Одесских катакомб: их сеть оценивают примерно "
            "в 2 500 км — ровно как весь наш маршрут."
        ),
    ),
    JourneyPlace(
        code="butuceni",
        distance_km=Decimal("825"),
        title="Бутучены · Старый Орхей",
        map_label="BUTUCENI",
        fact="Здесь действует монастырь с храмами, высеченными прямо в известняковой скале.",
    ),
    JourneyPlace(
        code="viscri",
        distance_km=Decimal("1050"),
        title="Вискри",
        map_label="VISCRI",
        fact="Село известно укреплённой церковью и входит в наследие ЮНЕСКО с 1999 года.",
    ),
    JourneyPlace(
        code="tokaj",
        distance_km=Decimal("1250"),
        title="Токай",
        map_label="TOKAJ",
        fact=(
            "Виноградники и лабиринты погребов Токая охраняются ЮНЕСКО; "
            "регион регулируется с 1737 года."
        ),
    ),
    JourneyPlace(
        code="budapest",
        distance_km=Decimal("1450"),
        title="Будапешт · Дунай",
        map_label="BUDAPEST",
        fact="Берега Дуная в центре Будапешта входят в объект Всемирного наследия ЮНЕСКО.",
    ),
    JourneyPlace(
        code="rust",
        distance_km=Decimal("1625"),
        title="Руст · Нойзидлер-Зе",
        map_label="RUST",
        fact=(
            "Рядом находится самое западное степное озеро Евразии "
            "и старинные винодельческие деревни."
        ),
    ),
    JourneyPlace(
        code="graz",
        distance_km=Decimal("1760"),
        title="Грац",
        map_label="GRAZ",
        fact="Город веками был перекрёстком германской, балканской и средиземноморской культур.",
    ),
    JourneyPlace(
        code="bled",
        distance_km=Decimal("1900"),
        title="Блед",
        map_label="BLED",
        fact="Посреди озера находится единственный природный остров Словении.",
    ),
    JourneyPlace(
        code="tarvisio",
        distance_km=Decimal("2030"),
        title="Тарвизио",
        map_label="TARVISIO",
        fact="Совсем рядом сходятся границы Италии, Словении и Австрии.",
    ),
    JourneyPlace(
        code="bellagio",
        distance_km=Decimal("2200"),
        title="Белладжо · озеро Комо",
        map_label="BELLAGIO",
        fact="Белладжо стоит на мысе, где озеро Комо расходится на два южных рукава.",
    ),
    JourneyPlace(
        code="aosta",
        distance_km=Decimal("2340"),
        title="Аоста",
        map_label="AOSTA",
        fact=(
            "Римляне основали Аосту в 25 году до н. э.; античные ворота "
            "и театр сохранились до сих пор."
        ),
    ),
    JourneyPlace(
        code="courmayeur",
        distance_km=Decimal("2440"),
        title="Курмайёр",
        map_label="COURMAYEUR",
        fact=(
            "Мы уже у итальянского подножия Монблана — до финиша остаётся "
            "последний альпийский рывок."
        ),
    ),
    JourneyPlace(
        code="chamonix",
        distance_km=JOURNEY_TARGET_KM,
        title="Шамони · Монблан",
        map_label="CHAMONIX",
        fact=(
            "В 1924 году Шамони принял соревнования, позже признанные "
            "первыми зимними Олимпийскими играми."
        ),
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
    current_place = JOURNEY_PLACES[0]
    next_place: JourneyPlace | None = None
    for place in JOURNEY_PLACES:
        if place.distance_km <= total:
            current_place = place
            continue
        next_place = place
        break
    remaining_to_next_place = (
        max(Decimal("0"), next_place.distance_km - total)
        if next_place is not None
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
        current_place=current_place,
        next_place=next_place,
        remaining_to_next_place_km=remaining_to_next_place.quantize(Decimal("0.01")),
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


def crossed_places(
    previous_total_km: Decimal,
    current_total_km: Decimal,
) -> tuple[JourneyPlace, ...]:
    previous = Decimal(previous_total_km)
    current = Decimal(current_total_km)
    if current <= previous:
        return ()
    return tuple(
        place
        for place in JOURNEY_PLACES[1:]
        if previous < place.distance_km <= current
    )


def place_milestone_code(place: JourneyPlace) -> str:
    return f"place:{place.code}"


def place_by_milestone_code(code: str) -> JourneyPlace:
    place_code = code.removeprefix("place:")
    return next(place for place in JOURNEY_PLACES if place.code == place_code)


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


def _track_point_at_distance(distance_km: Decimal) -> tuple[int, int]:
    distance = min(max(Decimal("0"), distance_km), JOURNEY_TARGET_KM)
    if distance >= JOURNEY_TARGET_KM:
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


def _point_at_progress(progress: JourneyProgress) -> tuple[int, int]:
    return _track_point_at_distance(progress.total_km)


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


def _draw_star(
    draw: ImageDraw.ImageDraw,
    center: tuple[int, int],
    *,
    radius: int,
    fill: tuple[int, int, int, int],
) -> None:
    x, y = center
    points = [
        (x, y - radius),
        (x + radius // 3, y - radius // 3),
        (x + radius, y),
        (x + radius // 3, y + radius // 3),
        (x, y + radius),
        (x - radius // 3, y + radius // 3),
        (x - radius, y),
        (x - radius // 3, y - radius // 3),
    ]
    draw.polygon(points, fill=fill)


def _draw_finish_flag(
    draw: ImageDraw.ImageDraw,
    anchor: tuple[int, int],
) -> None:
    x, y = anchor
    draw.line((x, y - 32, x, y + 10), fill=INK, width=4)
    draw.polygon(
        [(x + 1, y - 31), (x + 30, y - 23), (x + 1, y - 14)],
        fill=CORAL,
        outline=INK,
    )


def _journey_level(progress: JourneyProgress) -> int:
    return next(
        index
        for index, place in reversed(tuple(enumerate(JOURNEY_PLACES, start=1)))
        if place.distance_km <= progress.total_km
    )


def render_journey_map(progress: JourneyProgress) -> bytes:
    image = _base_map().copy().convert("RGBA")
    overlay = Image.new("RGBA", MAP_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    route_points = [point for _, point in ROUTE_TRACK]
    draw.line(route_points, fill=(45, 52, 61, 125), width=14, joint="curve")
    draw.line(route_points, fill=(255, 249, 225, 245), width=8, joint="curve")
    travelled = _travelled_polyline(progress)
    if len(travelled) > 1:
        draw.line(travelled, fill=(45, 52, 61, 145), width=15, joint="curve")
        draw.line(travelled, fill=CORAL, width=9, joint="curve")

    for place in JOURNEY_PLACES[1:-1]:
        x, y = _track_point_at_distance(place.distance_km)
        reached = place.distance_km <= progress.total_km
        fill = SUN if reached else (255, 249, 225, 255)
        draw.ellipse(
            (x - 5, y - 5, x + 5, y + 5),
            fill=fill,
            outline=INK,
            width=2,
        )

    for checkpoint in JOURNEY_CHECKPOINTS:
        x, y = checkpoint.point
        reached = checkpoint.distance_km <= progress.total_km
        fill = SUN if reached else CREAM
        draw.ellipse(
            (x - 10, y - 10, x + 10, y + 10),
            fill=fill,
            outline=LAVENDER,
            width=4,
        )
        if reached:
            _draw_star(draw, (x, y), radius=5, fill=CORAL)

    if progress.next_place is not None:
        next_x, next_y = _track_point_at_distance(progress.next_place.distance_km)
        draw.ellipse(
            (next_x - 12, next_y - 12, next_x + 12, next_y + 12),
            outline=MINT,
            width=4,
        )

    _draw_finish_flag(draw, (57, 329))

    marker_x, marker_y = _point_at_progress(progress)
    draw.polygon(
        [
            (marker_x - 9, marker_y + 12),
            (marker_x + 9, marker_y + 12),
            (marker_x, marker_y + 27),
        ],
        fill=CORAL,
        outline=INK,
    )
    draw.ellipse(
        (marker_x - 19, marker_y - 19, marker_x + 19, marker_y + 19),
        fill=CORAL,
        outline=INK,
        width=4,
    )
    _draw_star(draw, (marker_x, marker_y), radius=10, fill=(255, 249, 225, 255))

    place_label = f"NEAR {progress.current_place.map_label}"
    label_font = _font(15)
    label_bbox = draw.textbbox((0, 0), place_label, font=label_font)
    label_width = label_bbox[2] - label_bbox[0] + 24
    label_height = 32
    label_x = max(18, min(MAP_SIZE[0] - label_width - 18, marker_x - label_width // 2))
    label_y = marker_y - 58 if marker_y > 110 else marker_y + 28
    draw.rounded_rectangle(
        (label_x, label_y, label_x + label_width, label_y + label_height),
        radius=14,
        fill=CREAM,
        outline=CORAL,
        width=3,
    )
    draw.text(
        (label_x + 12, label_y + 8),
        place_label,
        font=label_font,
        fill=INK,
    )

    draw.rounded_rectangle(
        (28, 25, 430, 105),
        radius=20,
        fill=CREAM,
        outline=LAVENDER,
        width=4,
    )
    draw.text((50, 42), "KUBAN TO MONT BLANC", font=_font(26), fill=INK)
    draw.text((50, 75), "2,500 KM TOGETHER / 2026", font=_font(15), fill=MINT)
    _draw_star(draw, (397, 51), radius=11, fill=SUN)

    level = _journey_level(progress)
    draw.rounded_rectangle(
        (452, 25, 620, 105),
        radius=20,
        fill=LAVENDER,
        outline=INK,
        width=3,
    )
    draw.text((473, 39), "LEVEL", font=_font(14), fill=(255, 249, 225, 255))
    draw.text(
        (473, 61),
        f"{level:02d} / {len(JOURNEY_PLACES):02d}",
        font=_font(27),
        fill=(255, 249, 225, 255),
    )

    draw.rounded_rectangle(
        (642, 25, 1172, 105),
        radius=20,
        fill=CREAM,
        outline=MINT,
        width=4,
    )
    if progress.next_place is None:
        draw.text((666, 39), "QUEST COMPLETE!", font=_font(15), fill=CORAL)
        draw.text((666, 63), "MONT BLANC UNLOCKED", font=_font(25), fill=INK)
        _draw_star(draw, (1135, 62), radius=15, fill=SUN)
    else:
        draw.text((666, 39), "NEXT QUEST", font=_font(14), fill=MINT)
        draw.text(
            (666, 63),
            progress.next_place.map_label,
            font=_font(23),
            fill=INK,
        )
        remaining_text = f"{progress.remaining_to_next_place_km:.0f} KM"
        remaining_bbox = draw.textbbox((0, 0), remaining_text, font=_font(19))
        draw.text(
            (1144 - (remaining_bbox[2] - remaining_bbox[0]), 65),
            remaining_text,
            font=_font(19),
            fill=CORAL,
        )

    draw.rounded_rectangle(
        (28, 575, 1172, 650),
        radius=22,
        fill=CREAM,
        outline=LAVENDER,
        width=4,
    )
    draw.text((50, 587), "TEAM XP", font=_font(13), fill=MINT)
    bar_left, bar_top, bar_right, bar_bottom = 145, 589, 935, 610
    draw.rounded_rectangle(
        (bar_left, bar_top, bar_right, bar_bottom),
        radius=10,
        fill=(219, 216, 204, 255),
    )
    ratio = min(1.0, float(progress.total_km / progress.target_km))
    fill_right = bar_left + round((bar_right - bar_left) * ratio)
    if fill_right > bar_left:
        draw.rounded_rectangle(
            (bar_left, bar_top, fill_right, bar_bottom),
            radius=10,
            fill=CORAL,
        )
    draw.text(
        (50, 620),
        f"{progress.total_km:.1f} / {progress.target_km:.0f} KM",
        font=_font(17),
        fill=INK,
    )
    draw.text(
        (1025, 601),
        f"{progress.percent:.1f}%",
        font=_font(23),
        fill=CORAL,
    )

    image = Image.alpha_composite(image, overlay).convert("RGB")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
