from typing import Any

from fastapi.testclient import TestClient

_FESTIVALS = "/api/v1/festivals"
_LIST_FIELDS = {
    "festival_id", "name", "region_code", "venue_name", "lat", "lng", "start_date",
    "end_date", "event_status", "thumbnail_url", "image_credit", "source", "last_synced_at",
}
_DETAIL_FIELDS = {
    "address", "overview", "fee_text", "homepage_url", "image_url", "image_copyright",
    "source_ref", "is_mock",
}
_ROWS = (
    (
        "fst_000001", "광화문 겨울빛 축제", "SEOUL", "광화문광장", 37.5759, 126.9768,
        "2026-11-20", "2026-12-31", "ongoing", "Type3", "무료",
    ),
    (
        "fst_000002", "한강 겨울 야시장", "SEOUL", "여의도 한강공원", 37.5284, 126.9327,
        "2026-12-05", "2026-12-07", "upcoming", "Type1", None,
    ),
    (
        "fst_000003", "부산 빛 축제", "BUSAN", "광복로 일대", 35.1003, 129.0337,
        "2026-11-15", "2026-11-30", "ongoing", "Type3", "무료",
    ),
    (
        "fst_000004", "해운대 모래 축제", "BUSAN", "해운대해수욕장", 35.1587, 129.1604,
        "2026-06-01", "2026-06-03", "ended", "Type3", None,
    ),
    (
        "fst_000005", "평창 송어 축제", "GANGWON", "오대천 일원", 37.5640, 128.3846,
        "2026-12-26", "2027-01-25", "upcoming", None, None,
    ),
    (
        "fst_000006", "장소 미정 축제", "GYEONGGI", None, None, None,
        None, None, "needs_review", None, None,
    ),
)


def _detail(client: TestClient, festival_id: str) -> dict[str, Any]:
    response = client.get(f"{_FESTIVALS}/{festival_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["is_mock"] is True
    return detail


def _list(client: TestClient, query: str = "") -> dict[str, Any]:
    response = client.get(f"{_FESTIVALS}{query}")
    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is True
    assert set(body) == {"items", "total", "page", "page_size", "is_mock"}
    assert all(set(item) == _LIST_FIELDS for item in body["items"])
    return body


def _ids(body: dict[str, Any]) -> list[str]:
    return [item["festival_id"] for item in body["items"]]


def test_R6_all_mock_festivals_match_seed_data(client: TestClient) -> None:
    items = {item["festival_id"]: item for item in _list(client)["items"]}
    assert set(items) == {row[0] for row in _ROWS}
    for row in _ROWS:
        festival_id, name, region, venue, lat, lng, start, end, status, kind, fee = row
        image_path = f"https://tong.visitkorea.or.kr/cms/resource/mock/{festival_id}"
        credit = "한국관광공사" if kind else None
        expected_item = {
            "festival_id": festival_id,
            "name": name,
            "region_code": region,
            "venue_name": venue,
            "lat": lat,
            "lng": lng,
            "start_date": start,
            "end_date": end,
            "event_status": status,
            "thumbnail_url": f"{image_path}_2.jpg" if kind else None,
            "image_credit": credit,
            "source": "tourapi",
            "last_synced_at": "2026-11-22T09:00:00+09:00",
        }
        assert items[festival_id] == expected_item
        assert _detail(client, festival_id) == {
            **expected_item,
            "address": f"{venue} 일대" if venue else None,
            "overview": f"{name} 소개(모의)",
            "fee_text": fee,
            "homepage_url": None,
            "image_url": f"{image_path}_1.jpg" if kind else None,
            "image_copyright": (
                {"type": kind, "credit": credit, "modify_allowed": kind == "Type1"}
                if kind else None
            ),
            "source_ref": festival_id.removeprefix("fst_"),
            "is_mock": True,
        }


def test_R7_list_defaults_and_sorts(client: TestClient) -> None:
    body = _list(client)
    assert body["total"] == 6
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert _ids(body) == [
        "fst_000004", "fst_000003", "fst_000001", "fst_000002", "fst_000005", "fst_000006",
    ]
    assert _ids(_list(client, "?sort=-start_date")) == [
        "fst_000005", "fst_000002", "fst_000001", "fst_000003", "fst_000004", "fst_000006",
    ]
    names = [item["name"] for item in _list(client, "?sort=name")["items"]]
    assert names == sorted(names)


def test_R7_region_and_status_filters(client: TestClient) -> None:
    seoul = _list(client, "?region=SEOUL")
    assert seoul["total"] == 2
    assert _ids(seoul) == ["fst_000001", "fst_000002"]
    assert _ids(_list(client, "?region=BUSAN&status=ongoing")) == ["fst_000003"]
    assert _ids(_list(client, "?status=cancelled")) == []


def test_R7_date_filters_use_inclusive_overlap(client: TestClient) -> None:
    assert _ids(_list(client, "?date_from=2026-12-01&date_to=2026-12-10")) == [
        "fst_000001", "fst_000002",
    ]
    assert _ids(_list(client, "?date_to=2026-06-01")) == ["fst_000004"]
    assert _ids(_list(client, "?date_from=2027-01-25")) == ["fst_000005"]
    assert _list(client, "?date_from=2026-01-01&date_to=2027-01-02")["total"] == 5


def test_R7_searches_names_and_venues(client: TestClient) -> None:
    assert _ids(_list(client, "?q=야시장")) == ["fst_000002"]
    assert _ids(_list(client, "?q=여의도")) == ["fst_000002"]


def test_R7_list_paginates_after_filtering_and_sorting(client: TestClient) -> None:
    body = _list(client, "?page_size=2&page=3")
    assert len(body["items"]) == 2
    assert _ids(body) == ["fst_000005", "fst_000006"]
    assert body["total"] == 6
    assert body["page"] == 3
    assert body["page_size"] == 2
    assert _ids(_list(client, "?region=SEOUL&sort=-start_date&page_size=1")) == [
        "fst_000002",
    ]


def test_R7_invalid_filters_return_422(client: TestClient) -> None:
    for query, field in (
        ("region=MARS", "region"),
        ("date_from=2026-12-10&date_to=2026-12-01", "date_from"),
        ("date_from=2026-01-01&date_to=2027-01-03", "date_to"),
        ("date_from=2026-2-03", "date_from"),
        ("date_to=2026-02-30", "date_to"),
        ("page_size=101", "page_size"),
        ("page=0", "page"),
        ("q=", "q"),
        ("q=" + "a" * 51, "q"),
        ("status=needs_review", "status"),
        ("sort=unknown", "sort"),
    ):
        response = client.get(f"{_FESTIVALS}?{query}")
        assert response.status_code == 422, query
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert field in error["message"]


def test_R8_details_follow_image_rules(client: TestClient) -> None:
    type3 = _detail(client, "fst_000001")
    assert set(type3) == _LIST_FIELDS | _DETAIL_FIELDS
    assert type3["image_copyright"]["type"] == "Type3"
    assert type3["image_copyright"]["modify_allowed"] is False
    assert type3["image_credit"] == "한국관광공사"
    type1 = _detail(client, "fst_000002")
    assert type1["image_copyright"]["type"] == "Type1"
    assert type1["image_copyright"]["modify_allowed"] is True
    without_image = _detail(client, "fst_000005")
    for field in ("image_url", "thumbnail_url", "image_credit", "image_copyright"):
        assert without_image[field] is None


def test_R8_missing_and_malformed_festival_ids(client: TestClient) -> None:
    absent = client.get(f"{_FESTIVALS}/fst_999999")
    assert absent.status_code == 404
    assert absent.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"
    invalid = client.get(f"{_FESTIVALS}/abc")
    assert invalid.status_code == 422
    error = invalid.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "festival_id" in error["message"]
