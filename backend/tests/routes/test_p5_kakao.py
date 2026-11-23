import json
import traceback
from typing import Any

import httpx2
import pytest

from api.providers.kakao import KakaoClient
from api.providers.route_base import ErrorKind, ProviderError
from . import FIXTURES, QUERY, TEST_KEY


@pytest.fixture(autouse=True)
def set_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAKAO_REST_API_KEY", TEST_KEY)


def test_P5_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAKAO_REST_API_KEY")
    with pytest.raises(ProviderError) as caught:
        KakaoClient()
    assert caught.value.kind == "config"
    assert caught.value.provider == "kakao"


@pytest.mark.parametrize(
    ("status", "payload", "kind"),
    [
        (401, json.loads((FIXTURES / "kakao_error_key.json").read_text()), "config"),
        (403, {}, "config"),
        (400, {"code": -10}, "quota"),
        (429, {}, "quota"),
        (200, {"status": "NO_RESULTS"}, "no_result"),
        (200, {"status": "STARTNODES_NULL"}, "no_result"),
        (200, {"status": "ENDNODES_NULL"}, "no_result"),
        (200, {"status": "EQUAL_POINTS"}, "no_result"),
        (200, {"status": "INVALID_REQUEST"}, "bad_request"),
        (503, {"status": "INVALID_REQUEST"}, "temporary"),
    ],
)
def test_P5_request_and_error_mapping(
    status: int, payload: dict[str, Any], kind: ErrorKind
) -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        assert request.method == "GET"
        assert request.url.scheme == "https"
        assert request.url.host == "dapi.kakao.com"
        assert request.url.path == "/v2/routing/publictraffic"
        assert dict(request.url.params) == {
            "start_x": "126.9905", "start_y": "37.5668",
            "end_x": "126.9844", "end_y": "37.5456",
        }
        assert request.headers["Authorization"] == f"KakaoAK {TEST_KEY}"
        assert request.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 3.0)
        return httpx2.Response(status, json={**payload, "message": TEST_KEY})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        client = KakaoClient(http)
        with pytest.raises(ProviderError) as caught:
            client.query(QUERY)
    assert caught.value.kind == kind
    assert calls == 1
    assert TEST_KEY not in repr(client)
    assert TEST_KEY not in caught.value.detail


@pytest.mark.parametrize(
    ("error", "kind"), [(httpx2.ReadTimeout, "timeout"), (httpx2.ConnectError, "temporary")]
)
def test_P5_transport_error_without_retry(
    error: type[httpx2.RequestError], kind: ErrorKind
) -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise error(TEST_KEY, request=request)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        with pytest.raises(ProviderError) as caught:
            KakaoClient(http).query(QUERY)
    assert caught.value.kind == kind
    assert calls == 1
    assert TEST_KEY not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(("city", "mode"), [("seoul", "bus"), ("busan", "subway")])
def test_P6_normalizes_synthetic_routes(city: str, mode: str) -> None:
    body = json.loads((FIXTURES / f"kakao_transit_{city}.json").read_text())
    calls = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        return httpx2.Response(200, json=body)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        client = KakaoClient(http)
        result = client.query(QUERY)
        body["routes"] *= 4
        multiple = client.query(QUERY)
    assert calls == ["/v2/routing/publictraffic"] * 2
    candidate, = result.candidates
    assert [entry["candidate_id"] for entry in multiple.candidates] == ["c1", "c2", "c3"]
    assert candidate["walk_m"] is None
    assert candidate["service_running"] is None
    assert result.notices == [
        "2차 공급원(카카오맵) 결과예요. 이 결과는 저장하지 않아 다시 보려면 새로 조회해야 해요.",
        "첫·끝 도보 정보가 없어요",
        "막차 확인 불가",
    ]
    assert candidate["mode_evidence"] == {
        "bus_crowding": {"status": "unsupported", "reason": "2차 공급원은 버스 혼잡 근거를 주지 않아요"}
    }
    raw_route = body["routes"][0]
    props = raw_route["properties"]
    assert candidate["duration_min"] == (18 if city == "seoul" else 20)
    assert candidate["distance_m"] == props["totalDistance"]
    assert candidate["transfers"] == props["transfers"]
    assert candidate["fare_krw"] == props["fare"]["value"]
    leg = candidate["legs"][0]
    raw_step = raw_route["steps"][0]
    leg_props = raw_step["properties"]
    lng, lat = raw_step["path"]["points"][0]
    assert leg["path"][0] == [lat, lng]
    assert all(33 <= lat <= 39 and 124 <= lng <= 132 for lat, lng in leg["path"])
    assert leg["mode"] == mode
    assert leg["duration_min"] == 11
    assert leg["line"] == leg_props["vehicles"][0]["name"]
    assert leg["stops"][0] == {"name": leg_props["stops"][0]["name"]}


def test_P7_search_place_preserves_label_and_queries_every_time() -> None:
    label = " 예시 장소 "
    documents = iter([
        [{"place_name": "공급원 이름", "x": "126.9", "y": "37.5", "address_name": "예시 주소"}],
        [],
    ])

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.method == "GET"
        assert str(request.url.copy_with(query=None)) == "https://dapi.kakao.com/v2/local/search/keyword.json"
        assert dict(request.url.params) == {"query": label, "size": "1"}
        assert request.headers["Authorization"] == f"KakaoAK {TEST_KEY}"
        return httpx2.Response(200, json={"documents": next(documents)})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        client = KakaoClient(http)
        assert client.search_place(label) == (37.5, 126.9, label)
        with pytest.raises(ProviderError) as caught:
            client.search_place(label)
    assert caught.value.kind == "no_result"
