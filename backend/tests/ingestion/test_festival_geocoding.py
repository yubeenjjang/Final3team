from pathlib import Path

import httpx2
import pytest
from sqlalchemy import Engine, text

from api.ingestion.festivals import collect

from .test_i8_collect import TEST_KEY, listing, output_files, run_collector

_KAKAO_FIXTURE_KEY = "fixture-kakao"
_ADDRESS = "전라남도 무안군 무안읍 무안로 123"


def _listing(address: str) -> httpx2.Response:
    payload = listing()
    body = payload["response"]["body"]
    item = body["items"]["item"][0] | {
        "addr1": address, "addr2": "", "mapy": "19.69", "mapx": "117.99", "lDongRegnCd": "46",
    }
    body.update(totalCount=1, items={"item": [item]})
    return httpx2.Response(200, json=payload)


def _address_response(address: str, lat: str = "34.99012345") -> httpx2.Response:
    return httpx2.Response(200, json={"documents": [
        {"y": lat, "x": "126.47890123", "road_address": {"address_name": address}},
    ]})


@pytest.fixture
def provider_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", TEST_KEY)
    monkeypatch.setenv("KAKAO_REST_API_KEY", _KAKAO_FIXTURE_KEY)


@pytest.mark.parametrize(
    ("address", "result", "lat", "status", "geocoded", "publishable"),
    [
        (_ADDRESS, "전남 무안군 무안읍 무안로 123", "34.99012345", 200, True, True),
        (_ADDRESS, "전남 신안군 무안로 123", "34.99012345", 200, False, False),
        (_ADDRESS, "전북 무안군 무안로 123", "34.99012345", 200, False, False),
        (_ADDRESS, "전남 무안군 무안로 123", "19", 200, False, False),
        (_ADDRESS, "전남 무안군 무안로 123", "34.99012345", 503, False, False),
        ("무안로 123", "전남 무안군 무안로 123", "34.99012345", 200, False, False),
        ("", "", "", 200, False, True),
    ],
)
def test_collect_applies_coordinate_policy(
    tmp_path: Path, provider_keys: None, address: str, result: str, lat: str, status: int,
    geocoded: bool, publishable: bool,
) -> None:
    lookups = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/searchFestival2"):
            return _listing(address)
        assert request.url.path == "/v2/local/search/address.json"
        assert request.headers["authorization"] == f"KakaoAK {_KAKAO_FIXTURE_KEY}"
        lookups.append(request.url.params["query"])
        return _address_response(result, lat) if status == 200 else httpx2.Response(status)

    assert run_collector(tmp_path, respond, "--no-detail") == 0
    records, report = output_files(tmp_path)
    [record] = records
    assert lookups == ([address] if address else [])
    assert (record["latitude"], record["longitude"]) == (
        (34.990123, 126.478901) if geocoded else (None, None)
    )
    assert record["coords_source"] == ("geocoded" if geocoded else None)
    assert record["publishable"] is publishable
    assert record["review_status"] == ("approved" if publishable else "pending")
    assert report["issues"] == {"coords_out_of_range": 1}
    assert not report["errors"]


@pytest.mark.db
def test_geocode_retry_updates_an_unchanged_listing(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, provider_keys: None,
) -> None:
    monkeypatch.setattr(collect, "create_ingestion_engine", lambda: db_engine)
    geocodes = iter([httpx2.Response(503), _address_response("전남 무안군 무안읍 무안로 123")])

    def respond(request: httpx2.Request) -> httpx2.Response:
        return _listing(_ADDRESS) if request.url.path.endswith("/searchFestival2") else next(geocodes)

    assert run_collector(tmp_path, respond, "--db", "--no-detail") == 0
    rows, _ = output_files(tmp_path)
    before = rows[0]["raw_checksum"]
    assert run_collector(tmp_path, respond, "--db", "--no-detail") == 0
    rows, report = output_files(tmp_path)
    assert rows[0]["raw_checksum"] == before
    assert report["db"]["updated"] == 1
    with db_engine.connect() as connection:
        assert connection.execute(text("""
            SELECT review_status, published_at IS NOT NULL, coords_source
            FROM festivals
        """)).one() == ("approved", True, "geocoded")


@pytest.mark.db
def test_legacy_row_without_coordinates_or_address_becomes_public(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, provider_keys: None,
) -> None:
    monkeypatch.setattr(collect, "create_ingestion_engine", lambda: db_engine)

    def respond(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path.endswith("/searchFestival2")
        return _listing("")

    assert run_collector(tmp_path, respond, "--db", "--no-detail") == 0
    with db_engine.begin() as connection:
        connection.execute(text("UPDATE festivals SET review_status = 'pending', published_at = NULL"))
    assert run_collector(tmp_path, respond, "--db", "--no-detail") == 0
    with db_engine.connect() as connection:
        assert connection.execute(text("""
            SELECT review_status, published_at IS NOT NULL, latitude, longitude, coords_source
            FROM festivals
        """)).one() == ("approved", True, None, None, None)
