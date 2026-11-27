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
BOUNDARY_REVIEW_DISTANCE_M = 25.0


@dataclass(frozen=True)
class SeoulArea:
    code: str
    name: str
    polygons: list[Polygon]
    centroid: Point | None = None


@dataclass(frozen=True)
class AreaClassification:
    auto_areas: tuple[SeoulArea, ...]
    near_boundary: bool


@dataclass(frozen=True)
class SeoulAreaCatalog:
    areas: tuple[SeoulArea, ...]
    source_url: str

    def get(self, code: str) -> SeoulArea | None:
        return next((area for area in self.areas if area.code == code), None)


def _parse_centroid(value: object) -> Point | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        lat, lng = value
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            return (float(lat), float(lng))
    return None


def _parse_polygons(geometry: object) -> list[Polygon]:
    if not isinstance(geometry, dict):
        return []
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return []
    if geom_type == "Polygon":
        return [coords]
    if geom_type == "MultiPolygon":
        return list(coords)
    return []


def area_geometry(area: SeoulArea | None) -> tuple[Point | None, list[Ring] | None]:
    """구역의 중심 좌표와 경계 링 목록을 (lat, lng) 순서로 반환한다.

    Polygon은 [외곽 링, 내부 구멍 링, ...] 순서이며,
    MultiPolygon은 포함된 모든 폴리곤의 링(각 폴리곤 외곽 링 우선)을 평탄화해 반환한다.
    카탈로그에 구역이나 도형이 없으면 (None, None)을 반환한다.
    """
    if area is None or not area.polygons:
        return None, None
    rings = [
        [(float(lat), float(lng)) for lat, lng in ring]
        for polygon in area.polygons
        for ring in polygon
        if ring
    ]
    if not rings:
        return None, None
    center = (float(area.centroid[0]), float(area.centroid[1])) if area.centroid is not None else None
    return center, rings


@lru_cache(maxsize=1)
def load_catalog() -> SeoulAreaCatalog:
    path = Path(__file__).resolve().parents[1] / "data" / "seoul_areas.json"
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    areas = tuple(
        SeoulArea(
            code=area["area_code"],
            name=area["area_name"],
            polygons=_parse_polygons(area.get("geometry")),
            centroid=_parse_centroid(area.get("centroid")),
        )
        for area in data["areas"]
    )
    return SeoulAreaCatalog(areas, data["metadata"]["source"]["url"])


def _lat_lng_scales(lat: float) -> tuple[float, float]:
    # 기준 위도의 WGS84 국소 접평면에서 위도·경도 1도 차이를 미터로 환산한다.
    latitude = radians(lat)
    eccentricity_sq = 0.00669437999014
    curvature = 1 - eccentricity_sq * sin(latitude) ** 2
    radius = 6378137 / sqrt(curvature)
    lat_scale = radians(radius * (1 - eccentricity_sq) / curvature)
    lng_scale = radians(radius * cos(latitude))
    return lat_scale, lng_scale


def point_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat_scale, lng_scale = _lat_lng_scales((lat1 + lat2) / 2)
    dx = (lng2 - lng1) * lng_scale
    dy = (lat2 - lat1) * lat_scale
    return sqrt(dx * dx + dy * dy)


def nearby_areas(
    lat: float, lng: float, areas: tuple[SeoulArea, ...]
) -> list[tuple[SeoulArea, float]]:
    lat_scale, lng_scale = _lat_lng_scales(lat)

    matches = []
    for area in areas:
        if not area.polygons:
            continue
        measured = [_polygon_distance(polygon, lat, lng, lat_scale, lng_scale) for polygon in area.polygons]
        distance = min(d for d, _ in measured)
        depth = max(depth for _, depth in measured)
        if distance <= _RADIUS_M + _DISTANCE_TOLERANCE_M:
            matches.append((area, min(distance, _RADIUS_M), depth))
    # 거리가 같으면(좌표가 여러 구역 안에 있으면) 경계에서 더 깊이 들어간 구역을 먼저 둔다.
    ordered = sorted(matches, key=lambda match: (match[1], -match[2], match[0].code))[:3]
    return [(area, distance) for area, distance, _ in ordered]


def classify_areas(
    lat: float,
    lng: float,
    areas: tuple[SeoulArea, ...],
    *,
    boundary_margin_m: float = BOUNDARY_REVIEW_DISTANCE_M,
) -> AreaClassification:
    """서울시 공식 구역 기준으로 좌표를 확실한 내부 / 경계 근처 / 범위 밖으로 분류한다."""
    lat_scale, lng_scale = _lat_lng_scales(lat)
    strict_inside: list[tuple[SeoulArea, float]] = []
    near_boundary = False

    for area in areas:
        if not area.polygons:
            continue
        measured = [_polygon_distance(polygon, lat, lng, lat_scale, lng_scale) for polygon in area.polygons]
        distance = min(d for d, _ in measured)
        depth = max(d_in for _, d_in in measured)
        if distance == 0.0 and depth > boundary_margin_m + _DISTANCE_TOLERANCE_M:
            strict_inside.append((area, depth))
        elif distance <= boundary_margin_m + _DISTANCE_TOLERANCE_M:
            near_boundary = True

    ordered = sorted(strict_inside, key=lambda item: (-item[1], item[0].code))[:3]
    return AreaClassification(
        auto_areas=tuple(area for area, _ in ordered),
        near_boundary=near_boundary and not ordered,
    )


def _polygon_distance(
    polygon: Polygon, lat: float, lng: float, lat_scale: float, lng_scale: float
) -> tuple[float, float]:
    """(경계까지 거리, 안쪽 깊이)를 미터로 돌려준다. 바깥이면 깊이 0, 안쪽이면 거리 0."""
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
            nearest_sq = min(nearest_sq, hole_distance_sq)
        else:
            return 0.0, sqrt(nearest_sq)
    distance = sqrt(nearest_sq)
    return (0.0, 0.0) if distance <= _DISTANCE_TOLERANCE_M else (distance, 0.0)
