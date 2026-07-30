from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

COMMAND_RE = re.compile(r"^\s*/run(?:@[A-Za-z0-9_]+)?(?:\s+|$)", re.IGNORECASE)
DISTANCE_RE = re.compile(
    r"(?<![\d.,])(?P<distance>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:км|km)?(?![\w.,])",
    re.IGNORECASE,
)


class RunParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedRun:
    distance_km: Decimal
    note: str | None


def parse_run_text(
    text: str | None,
    *,
    max_distance_km: Decimal,
    require_command: bool = True,
) -> ParsedRun:
    if not text or not text.strip():
        raise RunParseError("Укажите дистанцию, например: /run 5.2")

    command = COMMAND_RE.match(text)
    if require_command and not command:
        raise RunParseError("Используйте команду /run 5.2")

    body = text[command.end() :] if command else text
    match = DISTANCE_RE.search(body)
    if not match:
        raise RunParseError("Не нашёл дистанцию. Пример: /run 5.2")

    raw_distance = match.group("distance").replace(",", ".")
    try:
        distance = Decimal(raw_distance)
    except InvalidOperation as exc:
        raise RunParseError("Не удалось прочитать дистанцию") from exc

    if distance <= 0:
        raise RunParseError("Дистанция должна быть больше нуля")
    if distance > max_distance_km:
        raise RunParseError(f"Максимальная дистанция за одну пробежку — {max_distance_km} км")

    distance = distance.quantize(Decimal("0.01"))
    note = f"{body[: match.start()]} {body[match.end() :]}".strip(" \t—–-:;,")
    note = re.sub(r"\s+", " ", note)
    return ParsedRun(distance_km=distance, note=note[:500] or None)
