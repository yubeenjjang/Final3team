import json
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from math import cos, radians, sin, sqrt
from pathlib import Path

Point = tuple[float, float]
Ring = list[Point]
Polygon = list[Ring]

_RADIUS_M = 1000
_DISTANCE_TOLERANCE_M = 1e-6


@dataclass(frozen=True)
class SeoulArea:
    code: str
    name: str
    polygons: list[Polygon]


@dataclass(frozen=True)
class SeoulAreaCatalog:
    areas: tuple[SeoulArea, ...]
    source_url: str


@lru_cache(maxsize=1)
def load_catalog() -> SeoulAreaCatalog:
    path = Path(__file__).resolve().parents[1] / "data" / "seoul_areas.json"
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    areas = tuple(
        SeoulArea(
            code=area["area_code"],
            name=area["area_name"],
            polygons=[area["geometry"]["coordinates"]]
            if area["geometry"]["type"] == "Polygon"
            else area["geometry"]["coordinates"],
        )
        for area in data["areas"]
    )
    return SeoulAreaCatalog(areas, data["metadata"]["source"]["url"])


def nearby_areas(
    lat: float, lng: float, areas: tuple[SeoulArea, ...]
) -> list[tuple[SeoulArea, float]]:
    # 축제 좌표의 WGS84 국소 접평면에서 위도·경도 차이를 미터로 바꾼다.
    latitude = radians(lat)
    eccentricity_sq = 0.00669437999014
    curvature = 1 - eccentricity_sq * sin(latitude) ** 2
    radius = 6378137 / sqrt(curvature)
    lat_scale = radians(radius * (1 - eccentricity_sq) / curvature)
    lng_scale = radians(radius * cos(latitude))

    matches = []
    for area in areas:
        distance = min(
            _polygon_distance(polygon, lat, lng, lat_scale, lng_scale)
            for polygon in area.polygons
        )
        if distance <= _RADIUS_M + _DISTANCE_TOLERANCE_M:
            matches.append((area, min(distance, _RADIUS_M)))
    return sorted(matches, key=lambda match: (match[1], match[0].code))[:3]


def _polygon_distance(
    polygon: Polygon, lat: float, lng: float, lat_scale: float, lng_scale: float
) -> float:
    def ring_distance(ring: Ring) -> tuple[bool, float]:
        points = (
            ((point_lng - lng) * lng_scale, (point_lat - lat) * lat_scale)
            for point_lat, point_lng in ring
        )
        inside = False
        nearest_sq = float("inf")
        for (ax, ay), (bx, by) in pairwise(points):
            dx, dy = bx - ax, by - ay
            if (ay > 0) != (by > 0) and ax - ay * dx / dy > 0:
                inside = not inside
            length_sq = dx * dx + dy * dy
            fraction = min(1.0, max(0.0, -(ax * dx + ay * dy) / length_sq)) if length_sq else 0.0
            nearest_sq = min(nearest_sq, (ax + fraction * dx) ** 2 + (ay + fraction * dy) ** 2)
        return inside, nearest_sq

    inside, nearest_sq = ring_distance(polygon[0])
    if inside:
        for hole in polygon[1:]:
            inside_hole, hole_distance_sq = ring_distance(hole)
            if inside_hole:
                nearest_sq = hole_distance_sq
                break
        else:
            return 0.0
    distance = sqrt(nearest_sq)
    return 0.0 if distance <= _DISTANCE_TOLERANCE_M else distance
