import logging
from collections.abc import Callable, Iterator
from datetime import date
from typing import TypeAlias
from pathlib import Path
from urllib.parse import unquote

import httpx2
import pytest

from api.providers.tourapi import TourApiClient, TourApiError

FIXTURES = Path(__file__).parent / "fixtures"
KEY_ENV = "DATA_GO_KR_SERVICE_KEY"
TEST_KEY = "TEST_KEY_DO_NOT_USE"
START = date(2026, 1, 1)
END = date(2026, 12, 31)
Handler: TypeAlias = Callable[[httpx2.Request], httpx2.Response]
ClientFactory: TypeAlias = Callable[[Handler], TourApiClient]


@pytest.fixture(autouse=True)
def set_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY_ENV, TEST_KEY)


@pytest.fixture
def make_client() -> Iterator[ClientFactory]:
    clients: list[httpx2.Client] = []

    def create(handler: Handler) -> TourApiClient:
        http = httpx2.Client(transport=httpx2.MockTransport(handler))
        clients.append(http)
        return TourApiClient(http)

    yield create
    for http in clients:
        http.close()


def empty_response() -> httpx2.Response:
    return httpx2.Response(200, content=(FIXTURES / "empty.json").read_bytes())


@pytest.mark.parametrize("key", [None, ""])
def test_I1_missing_key(monkeypatch: pytest.MonkeyPatch, key: str | None) -> None:
    if key is None:
        monkeypatch.delenv(KEY_ENV)
    else:
        monkeypatch.setenv(KEY_ENV, key)
    with pytest.raises(TourApiError) as caught:
        TourApiClient()
    assert caught.value.code == "NO_KEY"


@pytest.mark.parametrize("encoded", [False, True])
def test_I1_request_config_and_secret_redaction(
    monkeypatch: pytest.MonkeyPatch,
    make_client: ClientFactory,
    caplog: pytest.LogCaptureFixture,
    encoded: bool,
) -> None:
    key = "%54" + TEST_KEY[1:] if encoded else TEST_KEY
    monkeypatch.setenv(KEY_ENV, key)
    caplog.set_level(logging.DEBUG)

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert str(request.url).startswith("https://apis.data.go.kr/B551011/KorService2/searchFestival2?")
        assert f"serviceKey={key}" in str(request.url)
        assert request.url.params["serviceKey"] == unquote(key)
        assert request.url.params["MobileOS"] == "ETC"
        assert request.url.params["MobileApp"] == "noldaga"
        assert request.url.params["_type"] == "json"
        assert request.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 10.0)
        return httpx2.Response(
            200, json={"response": {"header": {"resultCode": "30", "resultMsg": f"{key} {TEST_KEY}"}}}
        )

    client = make_client(handler)
    with pytest.raises(TourApiError) as caught:
        client.search_festivals(START)
    assert caught.value.code == "RESULT_ERROR"
    assert caught.value.detail == "*** ***"
    for secret in {key, TEST_KEY}:
        assert secret not in str(caught.value)
        assert secret not in repr(caught.value)
        assert secret not in repr(client)
        assert secret not in caplog.text
    assert "serviceKey=***" in caplog.text


@pytest.mark.parametrize("success", [True, False])
def test_I1_retries_5xx_once(make_client: ClientFactory, success: bool) -> None:
    responses = iter([httpx2.Response(503), empty_response() if success else httpx2.Response(502)])
    client = make_client(lambda request: next(responses))
    if success:
        assert client.search_festivals(START) == []
    else:
        with pytest.raises(TourApiError) as caught:
            client.search_festivals(START)
        assert caught.value.code == "HTTP_ERROR"
    assert client.calls == {"searchFestival2": 2}


@pytest.mark.parametrize("error", [httpx2.ConnectError, httpx2.ReadTimeout])
def test_I1_retries_transport_errors_once(
    make_client: ClientFactory, error: type[httpx2.RequestError]
) -> None:
    attempts = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise error(str(request.url), request=request)
        return empty_response()

    client = make_client(handler)
    assert client.search_festivals(START) == []
    assert client.calls == {"searchFestival2": 2}


def test_I2_lists_all_pages(make_client: ClientFactory) -> None:
    page_numbers = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        query = request.url.params
        assert query["eventStartDate"] == "20260101"
        assert query["eventEndDate"] == "20261231"
        assert query["arrange"] == "A"
        assert query["numOfRows"] == "100"
        page = int(query["pageNo"])
        page_numbers.append(page)
        items = [{"contentid": str(i)} for i in range((page - 1) * 100, min(page * 100, 250))]
        return httpx2.Response(
            200,
            json={"response": {
                "header": {"resultCode": "0000"},
                "body": {"totalCount": 250, "items": {"item": items}},
            }},
        )

    client = make_client(handler)
    assert [item["contentid"] for item in client.search_festivals(START, END)] == [
        str(i) for i in range(250)
    ]
    assert page_numbers == [1, 2, 3]
    assert client.calls["searchFestival2"] == 3


def test_I2_empty_items(make_client: ClientFactory) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert "eventEndDate" not in request.url.params
        return empty_response()

    assert make_client(handler).search_festivals(START) == []


def test_I2_details_wrap_single_dictionary(make_client: ClientFactory) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        endpoint = request.url.path.rsplit("/", 1)[-1]
        assert request.url.params["contentId"] == "3379778"
        if endpoint == "detailIntro2":
            assert request.url.params["contentTypeId"] == "15"
        else:
            assert endpoint == "detailCommon2"
        return httpx2.Response(
            200, json={"response": {
                "header": {"resultCode": "0000"},
                "body": {"items": {"item": {"contentid": "3379778", "endpoint": endpoint}}},
            }}
        )

    client = make_client(handler)
    assert client.get_common("3379778") == {"contentid": "3379778", "endpoint": "detailCommon2"}
    assert client.get_intro("3379778") == {"contentid": "3379778", "endpoint": "detailIntro2"}
    assert client.calls == {"detailCommon2": 1, "detailIntro2": 1}


@pytest.mark.parametrize(
    ("status", "body", "code", "detail"),
    [
        (200, '{"response":{"header":{"resultCode":"30","resultMsg":"오류"}}}', "RESULT_ERROR", "오류"),
        (200, "<error>" + "오류" * 200 + "</error>", "RESULT_ERROR", ("<error>" + "오류" * 200)[:200]),
        (403, (FIXTURES / "error_key.txt").read_text(), "KEY_ERROR", None),
        (400, "SERVICE_KEY", "KEY_ERROR", None),
        (404, "", "HTTP_ERROR", None),
    ],
)
def test_I2_response_errors_without_retry(
    make_client: ClientFactory, status: int, body: str, code: str, detail: str | None
) -> None:
    client = make_client(lambda request: httpx2.Response(status, text=body))
    with pytest.raises(TourApiError) as caught:
        client.search_festivals(START)
    assert caught.value.code == code
    assert caught.value.detail == detail
    assert client.calls["searchFestival2"] == 1
