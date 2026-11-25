from pathlib import Path

import httpx2
import pytest
from sqlalchemy import Engine, text


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


@pytest.fixture
def provider_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", TEST_KEY)
    monkeypatch.setenv("KAKAO_REST_API_KEY", _KAKAO_FIXTURE_KEY)


@pytest.mark.parametrize("address", [_ADDRESS, "무안로 123", ""])
def test_out_of_range_coordinates_are_not_geocoded_and_stay_public_without_marker(
    tmp_path: Path, provider_keys: None, address: str,
) -> None:
    """카카오 주소 검색 결과는 저장할 수 없으므로 좌표를 보정하지 않는다(DB 설계서 6-3 coords_source)."""
    def respond(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path.endswith("/searchFestival2"), "카카오 등 다른 공급원을 부르면 안 됨"
        return _listing(address)

    assert run_collector(tmp_path, respond, "--no-detail") == 0
    records, report = output_files(tmp_path)
    [record] = records
    assert (record["latitude"], record["longitude"], record["coords_source"]) == (None, None, None)
    assert record["publishable"] is True and record["review_status"] == "approved"
    assert report["issues"] == {"coords_out_of_range": 1}
    assert not report["errors"]


@pytest.mark.db
def test_legacy_row_without_coordinates_or_address_becomes_public(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, provider_keys: None,
) -> None:

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
