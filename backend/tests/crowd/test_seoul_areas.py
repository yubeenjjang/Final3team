import pytest

from api.services.seoul_areas import (
    SeoulArea,
    area_geometry,
    classify_areas,
    load_catalog,
    nearby_areas,
    point_distance_m,
)


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
    # 둘 다 거리 0이면 안쪽 깊이가 깊은 inside가 경계 위의 edge보다 먼저
    assert [area.code for area, _ in matches] == ["inside", "edge", "boundary"]
    assert [distance for _, distance in matches] == pytest.approx([0, 0, 1000])


def test_P1_ties_inside_several_areas_order_by_depth_not_code() -> None:
    # 서울빛초롱축제처럼 좌표가 세 구역 안에 모두 있으면 경계에서 가장 깊은 구역이 대표가 된다.
    shallow = _box("A_shallow", -0.0001, 0.02)
    middle = _box("B_middle", -0.002, 0.02)
    deep = _box("C_deep", -0.01, 0.02)
    matches = nearby_areas(0, 0, (shallow, middle, deep))
    assert [area.code for area, _ in matches] == ["C_deep", "B_middle", "A_shallow"]
    assert [distance for _, distance in matches] == [0, 0, 0]


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


def test_P1_catalog_geometry_and_missing_cases() -> None:
    catalog = load_catalog()
    assert catalog.get("POI999") is None
    for area in catalog.areas:
        center, rings = area_geometry(area)
        assert center is not None and rings is not None and len(rings) >= 1
        assert 37.0 <= center[0] <= 38.0 and 126.0 <= center[1] <= 128.0
        for ring in rings:
            assert len(ring) >= 4
            for lat, lng in ring:
                assert 37.0 <= lat <= 38.0 and 126.0 <= lng <= 128.0

    # 내부 구멍이 있는 공식 Polygon(외곽 링 우선)
    dream_forest = catalog.get("POI096")
    _, df_rings = area_geometry(dream_forest)
    assert df_rings is not None and len(df_rings) == 2

    # MultiPolygon은 모든 폴리곤의 링을 외곽 우선으로 평탄화해 포함
    outer = _box("outer", 37.50, 37.52).polygons[0][0]
    hole = _box("hole", 37.505, 37.515).polygons[0][0]
    second = _box("second", 37.55, 37.56).polygons[0][0]
    multi = SeoulArea("MULTI", "멀티", [[outer, hole], [second]], centroid=(37.51, 126.98))
    center, multi_rings = area_geometry(multi)
    assert center == (37.51, 126.98)
    assert multi_rings == [outer, hole, second]

    # 카탈로그에 없거나 도형이 없으면 (None, None)
    assert area_geometry(None) == (None, None)
    assert area_geometry(SeoulArea("EMPTY", "빈구역", [], centroid=(37.5, 127.0))) == (None, None)


def test_P1_point_distance_and_classify_areas() -> None:
    # 적도에서 위도 1도 ≈ 110,574m
    deg_25m = 25.0 / 110574.275821595
    assert point_distance_m(0.0, 0.0, deg_25m, 0.0) == pytest.approx(25.0, abs=0.1)

    deep = _box("A_deep", -0.005, 0.005)
    mid = _box("B_mid", -0.002, 0.002)
    shallow = _box("C_shallow", -0.0001, 0.0001)  # 깊이 ≈ 11m <= 25m
    near_outside = _box("D_near_out", deg_25m * 0.5, 0.002)  # 바깥 ≈ 12.5m <= 25m
    far_outside = _box("E_far_out", deg_25m * 4.0, 0.005)  # 바깥 ≈ 100m > 25m

    # 확실한 내부(>25m) 구역이 있으면 깊이순 최대 3곳 자동 승인, 경계 근처(<=25m)는 제외
    res_auto = classify_areas(0.0, 0.0, (shallow, mid, deep, near_outside, far_outside))
    assert [a.code for a in res_auto.auto_areas] == ["A_deep", "B_mid"]
    assert res_auto.near_boundary is False

    # 내부이지만 경계 25m 이내만 있으면 검토 대상
    res_near_in = classify_areas(0.0, 0.0, (shallow, far_outside))
    assert res_near_in.auto_areas == ()
    assert res_near_in.near_boundary is True

    # 외부이지만 경계 25m 이내이면 검토 대상
    res_near_out = classify_areas(0.0, 0.0, (near_outside, far_outside))
    assert res_near_out.auto_areas == ()
    assert res_near_out.near_boundary is True

    # 모든 구역 바깥 25m 초과면 관측 범위 밖
    res_outside = classify_areas(0.0, 0.0, (far_outside,))
    assert res_outside.auto_areas == ()
    assert res_outside.near_boundary is False
