import os
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from api.ingestion.festivals.normalize import KST
from api.services import festival_store

pytestmark = pytest.mark.db

_URL = "/api/v1/festivals"


@pytest.fixture
def app_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DB_APP_URL")
    if not url or not os.environ.get("TEST_DB_URL"):
        pytest.skip("일회용 DB의 TEST_DB_URL과 TEST_DB_APP_URL이 필요합니다.")
    engine = create_engine(url, hide_parameters=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def catalog_client(
    app_engine: Engine, db_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    from api.main import app

    now = datetime.now(KST)
    today = now.date()
    rows = [
        ("fst_I12001", "봄맞이 50% 축제", "SEOUL", "중앙 광장", -1, 1, "ended", "approved", "festival"),
        ("fst_I12002", "가을 축제", "BUSAN", "바다 공원", 2, 4, "ongoing", "approved", "festival"),
        ("fst_I12003", "여름_축제", "SEOUL", "시민 공원", 2, 4, "cancelled", "approved", "festival"),
        ("fst_I12004", "검토 중 축제", "SEOUL", "북쪽 광장", 0, 1, "ongoing", "pending", "festival"),
        ("fst_I12005", "박람회", "SEOUL", "북쪽 광장", 0, 1, "ongoing", "approved", "event"),
    ]
    with db_engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO data_sources (
                source_id, name, provider_org, scope, is_realtime, refresh_s, key_site, status
            ) VALUES (
                'tourapi', '한국관광공사 TourAPI', '한국관광공사', 'national',
                FALSE, 86400, 'data.go.kr', 'verified'
            )
            ON CONFLICT (source_id) DO NOTHING
        """))
        connection.execute(text("""
            INSERT INTO festivals (
                festival_id, title, region_code, venue_name, start_date, end_date,
                event_status, review_status, category, source_class_level2, published_at, last_synced_at,
                latitude, longitude, summary, admission_fee_text, official_url, address
            ) VALUES (
                :id, :title, :region, :venue, :start_date, :end_date,
                :status, :review, :category, :source_class, :now, :now,
                37.5, 127.1, '축제 소개', '무료', 'https://example.invalid', '축제 주소'
            )
        """), [
            dict(id=festival_id, title=title, region=region, venue=venue, status=status,
                 review=review, category=category, source_class="EV01" if category == "festival" else "EV03",
                 now=now, start_date=today + timedelta(days=start),
                 end_date=today + timedelta(days=end))
            for festival_id, title, region, venue, start, end, status, review, category in rows
        ])
        connection.execute(text("""
            INSERT INTO festival_sources (festival_id, source_id, source_item_id, fetched_at, raw_checksum)
            VALUES ('fst_I12001', 'tourapi', '1234567', :now, 'catalog-test')
        """), {"now": now})
        connection.execute(text("""
            UPDATE festivals
            SET image_url = 'https://tong.visitkorea.or.kr/cms/resource/mock/fst_I12001_1.jpg',
                thumbnail_url = 'https://tong.visitkorea.or.kr/cms/resource/mock/fst_I12001_2.jpg',
                image_copyright_type = 'Type3'
            WHERE festival_id = 'fst_I12001'
        """))

    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setattr(festival_store, "get_festival_engine", lambda: app_engine)
    with TestClient(app) as client:
        yield client


def test_I12_catalog_returns_public_festivals_and_filters_in_db(catalog_client: TestClient) -> None:
    response = catalog_client.get(_URL)
    assert response.status_code == 200
    assert "X-Mock" not in response.headers
    page = response.json()
    assert page["is_mock"] is False
    assert page["total"] == 3
    assert [(item["festival_id"], item["event_status"]) for item in page["items"]] == [
        ("fst_I12001", "ongoing"), ("fst_I12002", "upcoming"), ("fst_I12003", "cancelled"),
    ]

    for params, expected in (
        ({"region": "SEOUL"}, ["fst_I12001", "fst_I12003"]),
        ({"q": "바다"}, ["fst_I12002"]),
        ({"q": "%"}, ["fst_I12001"]),
        ({"q": "_"}, ["fst_I12003"]),
        ({"status": " ongoing, upcoming, ongoing "}, ["fst_I12001", "fst_I12002"]),
        ({"status": "cancelled"}, ["fst_I12003"]),
    ):
        response = catalog_client.get(_URL, params=params)
        assert response.status_code == 200
        assert response.json()["total"] == len(expected)
        assert [item["festival_id"] for item in response.json()["items"]] == expected

    response = catalog_client.get(_URL, params={"page": 3, "page_size": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert [item["festival_id"] for item in response.json()["items"]] == ["fst_I12003"]


def test_I12_catalog_detail_reads_tourapi_source(catalog_client: TestClient) -> None:
    response = catalog_client.get(f"{_URL}/fst_I12001")
    assert response.status_code == 200
    assert "X-Mock" not in response.headers
    detail = response.json()
    assert detail["is_mock"] is False
    assert detail["name"] == "봄맞이 50% 축제"
    assert detail["overview"] == "축제 소개"
    assert detail["fee_text"] == "무료"
    assert detail["homepage_url"] == "https://example.invalid"
    assert detail["lat"] == 37.5
    assert detail["lng"] == 127.1
    assert detail["image_credit"] == "한국관광공사"
    assert detail["image_copyright"] == {
        "type": "Type3", "credit": "한국관광공사", "modify_allowed": False,
    }
    assert detail["event_status"] == "ongoing"
    assert detail["source"] == "tourapi"
    assert detail["source_ref"] == "1234567"

    for festival_id in ("fst_I12004", "fst_I12005", "fst_missing"):
        response = catalog_client.get(f"{_URL}/{festival_id}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"
