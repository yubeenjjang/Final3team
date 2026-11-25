import pytest

from api.services.seoul_areas import SeoulArea, load_catalog, nearby_areas


def _box(code: str, south: float, north: float) -> SeoulArea:
    return SeoulArea(
        code, code,
        [[[(south, -0.01), (south, 0.01), (north, 0.01), (north, -0.01), (south, -0.01)]]],
    )


def test_P1_official_areas_use_latitude_longitude_order() -> None:
    areas = load_catalog().areas
    assert len(areas) == len({area.code for area in areas}) == 121
    gwanghwamun = next(area for area in areas if area.code == "POI009")
    assert nearby_areas(37.5709305, 126.9771863, (gwanghwamun,)) == [(gwanghwamun, 0)]


def test_P1_polygon_interior_edge_and_inclusive_radius() -> None:
    # WGS84 적도 위도 1도의 길이로 만든 합성 구역 경계.
    radius_lat = 1000 / 110574.275821595
    inside = _box("inside", -0.01, 0.01)
    edge = _box("edge", 0, 0.02)
    boundary = _box("boundary", radius_lat, 0.02)
    outside = _box("outside", radius_lat * 1.0001, 0.02)
    matches = nearby_areas(0, 0, (outside, inside, boundary, edge))
    assert [area.code for area, _ in matches] == ["edge", "inside", "boundary"]
    assert [distance for _, distance in matches] == pytest.approx([0, 0, 1000])


def test_P1_sorts_by_boundary_and_selects_only_three() -> None:
    areas = (
        _box("far", 0.008, 0.009),
        _box("mid", 0.004, 0.02),
        _box("near", 0.002, 0.05),
        _box("inside", -0.001, 0.04),
    )
    matches = nearby_areas(0, 0, areas)
    assert [area.code for area, _ in matches] == ["inside", "near", "mid"]
    assert [distance for _, distance in matches] == pytest.approx([0, 221.14855, 442.2971])


def test_P1_polygon_hole_and_disconnected_polygon() -> None:
    outer = _box("outer", -0.02, 0.02).polygons[0][0]
    hole = _box("hole", -0.002, 0.002).polygons[0][0]
    separated = _box("separated", 0.1, 0.2).polygons[0]
    area = SeoulArea("A", "A", [[outer, hole], separated])
    ((_, distance),) = nearby_areas(0, 0, (area,))
    assert distance == pytest.approx(221.14855)
    assert nearby_areas(0.15, 0, (area,)) == [(area, 0)]
