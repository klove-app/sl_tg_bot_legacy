from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path

TARGET_KM = 2500.0
INTERVAL_KM = 12.5
ALLOWED_COUNTRIES = {"AT", "FR", "HR", "HU", "IT", "MD", "RO", "RU", "SI", "SK", "UA"}
NATIVE_LANGUAGES = {
    "AT": "de",
    "FR": "fr",
    "HR": "hr",
    "HU": "hu",
    "IT": "it",
    "MD": "ro",
    "RO": "ro",
    "RU": "ru",
    "SI": "sl",
    "SK": "sk",
    "UA": "uk",
}


@dataclass(frozen=True)
class RouteAnchor:
    code: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PopulatedPlace:
    geoname_id: int
    name: str
    ascii_name: str
    latitude: float
    longitude: float
    country_code: str
    population: int


ROUTE_ANCHORS = (
    RouteAnchor("krasnodar", 45.0355, 38.9753),
    RouteAnchor("slavyansk_na_kubani", 45.2558, 38.1256),
    RouteAnchor("temryuk", 45.2722, 37.3811),
    RouteAnchor("taman", 45.2117, 36.7161),
    RouteAnchor("kerch", 45.3562, 36.4674),
    RouteAnchor("feodosiya", 45.0319, 35.3824),
    RouteAnchor("dzhankoi", 45.7117, 34.3937),
    RouteAnchor("kherson", 46.6354, 32.6169),
    RouteAnchor("nerubayske", 46.5500, 30.6300),
    RouteAnchor("chisinau", 47.0105, 28.8638),
    RouteAnchor("butuceni", 47.3100, 28.9700),
    RouteAnchor("iasi", 47.1585, 27.6014),
    RouteAnchor("bacau", 46.5670, 26.9146),
    RouteAnchor("brasov", 45.6427, 25.5887),
    RouteAnchor("viscri", 46.0553, 25.0930),
    RouteAnchor("sighisoara", 46.2197, 24.7964),
    RouteAnchor("targu_mures", 46.5425, 24.5575),
    RouteAnchor("cluj_napoca", 46.7712, 23.6236),
    RouteAnchor("oradea", 47.0465, 21.9189),
    RouteAnchor("tokaj", 48.1170, 21.4090),
    RouteAnchor("miskolc", 48.1035, 20.7784),
    RouteAnchor("budapest", 47.4979, 19.0402),
    RouteAnchor("gyor", 47.6875, 17.6504),
    RouteAnchor("rust", 47.8000, 16.6750),
    RouteAnchor("graz", 47.0707, 15.4395),
    RouteAnchor("bled", 46.3683, 14.1146),
    RouteAnchor("tarvisio", 46.5057, 13.5786),
    RouteAnchor("udine", 46.0711, 13.2346),
    RouteAnchor("verona", 45.4384, 10.9916),
    RouteAnchor("bergamo", 45.6983, 9.6773),
    RouteAnchor("bellagio", 45.9876, 9.2612),
    RouteAnchor("novara", 45.4469, 8.6212),
    RouteAnchor("ivrea", 45.4673, 7.8767),
    RouteAnchor("aosta", 45.7375, 7.3201),
    RouteAnchor("courmayeur", 45.7919, 6.9710),
    RouteAnchor("chamonix", 45.9237, 6.8694),
)


def haversine_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_km = 6371.0088
    latitude_a_rad = math.radians(latitude_a)
    latitude_b_rad = math.radians(latitude_b)
    latitude_delta = latitude_b_rad - latitude_a_rad
    longitude_delta = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a_rad)
        * math.cos(latitude_b_rad)
        * math.sin(longitude_delta / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def load_populated_places(path: Path) -> list[PopulatedPlace]:
    places: list[PopulatedPlace] = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            columns = line.rstrip("\n").split("\t")
            country_code = columns[8]
            latitude = float(columns[4])
            longitude = float(columns[5])
            if country_code not in ALLOWED_COUNTRIES:
                continue
            if not (43.5 <= latitude <= 50.0 and 5.0 <= longitude <= 40.0):
                continue
            places.append(
                PopulatedPlace(
                    geoname_id=int(columns[0]),
                    name=columns[1],
                    ascii_name=columns[2] or columns[1],
                    latitude=latitude,
                    longitude=longitude,
                    country_code=country_code,
                    population=int(columns[14] or 0),
                )
            )
    return places


def route_geometry() -> tuple[list[float], float]:
    cumulative = [0.0]
    for start, end in zip(ROUTE_ANCHORS, ROUTE_ANCHORS[1:], strict=False):
        cumulative.append(
            cumulative[-1]
            + haversine_km(
                start.latitude,
                start.longitude,
                end.latitude,
                end.longitude,
            )
        )
    return cumulative, cumulative[-1]


def coordinate_at_distance(
    route_km: float,
    cumulative: list[float],
    physical_total_km: float,
) -> tuple[float, float]:
    target_physical_km = route_km / TARGET_KM * physical_total_km
    for index, segment_end in enumerate(cumulative[1:], start=1):
        if target_physical_km > segment_end:
            continue
        segment_start = cumulative[index - 1]
        ratio = (target_physical_km - segment_start) / (segment_end - segment_start)
        start = ROUTE_ANCHORS[index - 1]
        end = ROUTE_ANCHORS[index]
        return (
            start.latitude + (end.latitude - start.latitude) * ratio,
            start.longitude + (end.longitude - start.longitude) * ratio,
        )
    finish = ROUTE_ANCHORS[-1]
    return finish.latitude, finish.longitude


def nearest_place(
    latitude: float,
    longitude: float,
    places: list[PopulatedPlace],
) -> tuple[PopulatedPlace, float]:
    return min(
        (
            (
                place,
                haversine_km(latitude, longitude, place.latitude, place.longitude),
            )
            for place in places
        ),
        key=lambda item: (item[1], -item[0].population),
    )


def load_localized_names(
    directory: Path | None,
    country_by_geoname_id: dict[int, str],
) -> dict[int, str]:
    if directory is None:
        return {}
    names: dict[int, tuple[int, str]] = {}
    for archive_path in sorted(directory.glob("*.zip")):
        with zipfile.ZipFile(archive_path) as archive:
            text_name = next(
                name
                for name in archive.namelist()
                if name.endswith(".txt") and not name.endswith("readme.txt")
            )
            with archive.open(text_name) as binary_source:
                with io.TextIOWrapper(binary_source, encoding="utf-8") as source:
                    for line in source:
                        columns = line.rstrip("\n").split("\t")
                        if len(columns) < 5:
                            continue
                        geoname_id = int(columns[1])
                        country_code = country_by_geoname_id.get(geoname_id)
                        if country_code is None:
                            continue
                        language = columns[2]
                        if language == "ru":
                            priority = 4
                        elif language == NATIVE_LANGUAGES[country_code]:
                            priority = 2
                        else:
                            continue
                        preferred = columns[4] == "1"
                        priority += int(preferred)
                        previous = names.get(geoname_id)
                        if previous is None or priority > previous[0]:
                            names[geoname_id] = (priority, columns[3])
    return {geoname_id: value for geoname_id, (_, value) in names.items()}


def generate(
    input_path: Path,
    output_path: Path,
    alternate_names_dir: Path | None = None,
) -> None:
    places = load_populated_places(input_path)
    cumulative, physical_total_km = route_geometry()
    major_distances = {
        anchor.code: round(cumulative[index] / physical_total_km * TARGET_KM, 1)
        for index, anchor in enumerate(ROUTE_ANCHORS)
    }

    raw_waypoints: list[tuple[float, float, float, PopulatedPlace, float]] = []
    waypoint_count = round(TARGET_KM / INTERVAL_KM)
    for index in range(waypoint_count + 1):
        route_km = min(TARGET_KM, index * INTERVAL_KM)
        latitude, longitude = coordinate_at_distance(
            route_km,
            cumulative,
            physical_total_km,
        )
        place, offset_km = nearest_place(latitude, longitude, places)
        raw_waypoints.append((route_km, latitude, longitude, place, offset_km))

    localized_names = load_localized_names(
        alternate_names_dir,
        {
            place.geoname_id: place.country_code
            for _, _, _, place, _ in raw_waypoints
        },
    )
    waypoints = []
    for route_km, latitude, longitude, place, offset_km in raw_waypoints:
        waypoints.append(
            {
                "code": f"km_{route_km:06.1f}".replace(".", "_"),
                "distance_km": f"{route_km:.1f}",
                "title": localized_names.get(place.geoname_id, place.name),
                "map_label": place.ascii_name.upper(),
                "country_code": place.country_code,
                "geoname_id": place.geoname_id,
                "latitude": round(latitude, 5),
                "longitude": round(longitude, 5),
                "place_offset_km": round(offset_km, 1),
            }
        )

    payload = {
        "source": "GeoNames cities500 and alternate names, CC BY 4.0",
        "source_url": "https://download.geonames.org/export/dump/",
        "generated_for": "Runforest 2026 Krasnodar-to-Mont-Blanc journey",
        "illustrative_only": True,
        "target_km": TARGET_KM,
        "interval_km": INTERVAL_KM,
        "localized_title_language": "ru-with-local-fallback",
        "physical_anchor_length_km": round(physical_total_km, 1),
        "major_distances": major_distances,
        "waypoints": waypoints,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--alternate-names-dir", type=Path)
    args = parser.parse_args()
    generate(args.input, args.output, args.alternate_names_dir)


if __name__ == "__main__":
    main()
