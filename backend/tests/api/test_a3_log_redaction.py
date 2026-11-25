import asyncio
import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from urllib.parse import unquote_plus

import h11
import httpx2
import pytest
from uvicorn import Config
from uvicorn.protocols.http.h11_impl import H11Protocol
from uvicorn.server import ServerState

from api.main import app
from api.providers.kakao import KakaoClient
from api.providers.seoul_citydata import SeoulCityData
from api.providers.tmap import TmapClient
from api.services import mock_routes, real_routes, seoul_crowd

_RETURN = "/api/v1/routes/return"
_CROWD = "/api/v1/festivals/fst_000001/crowd"
_ORIGIN = {"lat": 37.512347, "lng": 126.945678}
_DESTINATION = {"lat": 37.543217, "lng": 127.012345}
_SEARCH_COORDINATES = {"lat": 37.581237, "lng": 126.987654}
_SEARCH = "합성 장소 광장 + 입구"
_KEYS = {
    "TMAP_APP_KEY": "fixture-tmap-key",
    "KAKAO_REST_API_KEY": "fixture-kakao-key",
    "SEOUL_OPEN_API_KEY": "fixture-seoul+key",
    "ROUTE_KEY_SECRET": "fixture-route-hmac-key",
}
_FIXTURES = Path(__file__).resolve().parents[1]


@pytest.fixture
def capture(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch,
) -> pytest.LogCaptureFixture:
    # Default Uvicorn access logging has its own handler and does not propagate.
    caplog.set_level(1)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.asgi", "uvicorn.error",
                 "httpx2", "httpcore2.http11"):
        caplog.set_level(1, logger=name)
        monkeypatch.setattr(logging.getLogger(name), "propagate", True)
    return caplog


@pytest.fixture
def server_config(capture: pytest.LogCaptureFixture) -> Config:
    config = Config(app, http="h11", ws="none", lifespan="off", log_config=None, proxy_headers=False)
    config.load()
    return config


@pytest.fixture
def mode(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch,
         tmp_path: Path) -> Iterator[tuple[str, list[str]]]:
    mode = request.param
    monkeypatch.setenv("FESTIVAL_DATA", "mock")
    monkeypatch.setenv("ROUTE_STORE", "memory")
    monkeypatch.setenv("ROUTE_PROVIDER", mode)
    monkeypatch.setenv("CROWD_PROVIDER", mode)
    monkeypatch.setenv("ROUTE_QUOTA_FILE", str(tmp_path / "route.json"))
    monkeypatch.setenv("CROWD_QUOTA_FILE", str(tmp_path / "crowd.json"))
    for name, key in _KEYS.items():
        monkeypatch.setenv(name, key)

    calls = []

    def send_route(request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        calls.append(path)
        logging.getLogger("httpcore2.http11").debug(
            "transport request target=%s headers=%s body=%r",
            request.url, dict(request.headers), request.content,
        )
        if path == "/v2/local/search/keyword.json":
            assert request.url.params["query"] == _SEARCH
            assert request.headers["authorization"] == f"KakaoAK {_KEYS['KAKAO_REST_API_KEY']}"
            return httpx2.Response(200, json={"documents": [
                {"y": str(_SEARCH_COORDINATES["lat"]), "x": str(_SEARCH_COORDINATES["lng"])}
            ]})
        if path == "/transit/routes":
            payload = json.loads(request.content)
            assert (payload["startY"], payload["startX"]) == tuple(_ORIGIN.values())
            assert request.headers["appkey"] == _KEYS["TMAP_APP_KEY"]
            if (payload["endY"], payload["endX"]) == tuple(_DESTINATION.values()):
                return httpx2.Response(503)
            assert (payload["endY"], payload["endX"]) == tuple(_SEARCH_COORDINATES.values())
            filename = "tmap_seoul.json"
        else:
            assert path == "/v2/routing/publictraffic"
            params = request.url.params
            assert tuple(float(params[name]) for name in ("start_y", "start_x")) == tuple(_ORIGIN.values())
            assert tuple(float(params[name]) for name in ("end_y", "end_x")) == tuple(_DESTINATION.values())
            filename = "kakao_transit_seoul.json"
        return httpx2.Response(200, json=json.loads(
            (_FIXTURES / "routes" / "fixtures" / filename).read_text(encoding="utf-8")
        ))

    def send_crowd(request: httpx2.Request) -> httpx2.Response:
        calls.append("citydata_ppltn")
        _, key, dataset, _, _, _, area_code = request.url.path.split("/")
        assert key == _KEYS["SEOUL_OPEN_API_KEY"]
        assert f"/{dataset}/citydata_ppltn/" in request.url.path
        payload = json.loads(
            (_FIXTURES / "crowd" / "fixtures" / "citydata_ppltn_observed.json").read_text(encoding="utf-8")
        )
        payload["SeoulRtd.citydata_ppltn"][0]["AREA_CD"] = area_code
        return httpx2.Response(200, json=payload)

    with httpx2.Client(transport=httpx2.MockTransport(send_route)) as http:
        routes = real_routes.RealRouteService(
            tmap=lambda: TmapClient(http), kakao=lambda: KakaoClient(http),
        )
        crowd = seoul_crowd.SeoulCrowdService(
            SeoulCityData(transport=httpx2.MockTransport(send_crowd)),
            now=lambda: datetime.fromisoformat("2026-11-19T17:26:00+09:00"),
        )
        monkeypatch.setattr(real_routes, "get_service", lambda: routes)
        monkeypatch.setattr(seoul_crowd, "get_service", lambda: crowd)
        yield mode, calls


async def _send(config: Config, request: httpx2.Request) -> httpx2.Response:
    """Run Uvicorn's HTTP parser and access logger with an in-memory transport."""
    outgoing = h11.Connection(h11.CLIENT)
    server = ServerState()
    protocol = H11Protocol(config, server, {})
    wire = bytearray()
    transport = Mock(spec=asyncio.Transport)
    transport.get_extra_info.return_value = None
    transport.write.side_effect = wire.extend
    transport.is_closing.return_value = False
    protocol.connection_made(transport)
    headers = list(request.headers.raw) + [(b"connection", b"close")]
    protocol.data_received(
        outgoing.send(h11.Request(method=request.method, target=request.url.raw_path, headers=headers))
        + outgoing.send(h11.Data(data=request.content))
        + outgoing.send(h11.EndOfMessage())
    )
    await asyncio.wait_for(asyncio.gather(*server.tasks), timeout=5)
    outgoing.receive_data(wire)
    response = outgoing.next_event()
    assert isinstance(response, h11.Response)
    body = bytearray()
    while isinstance(event := outgoing.next_event(), h11.Data):
        body.extend(event.data)
    assert isinstance(event, h11.EndOfMessage)
    return httpx2.Response(response.status_code, headers=response.headers, content=bytes(body))


def _assert_no_raw_logs(logs: str, forbidden: dict[str, str]) -> None:
    decoded = unquote_plus(logs)
    leaked = [
        label for label, value in forbidden.items()
        if value in logs or value in decoded or json.dumps(value)[1:-1] in logs
    ]
    if leaked:
        pytest.fail(f"로그에 원문 발견: {', '.join(leaked)}")


@pytest.mark.parametrize("mode", ["mock", "real"], indirect=True)
def test_a3_requests_keep_ids_and_status_without_raw_inputs(
    mode: tuple[str, list[str]], capture: pytest.LogCaptureFixture, server_config: Config,
) -> None:
    mode_name, calls = mode

    async def exercise() -> tuple[dict[str, str], dict[str, str]]:
        tokens = {}
        route_ids = {"crowd": "-"}

        async def check(method, path, name, status, *, params=None, payload=None, token=None):
            request_id = f"a3-{mode_name}-{name}"
            headers = {"X-Request-ID": request_id}
            if method == "POST":
                headers["X-Mock-Scenario"] = "sync_ready"
            if token:
                headers["X-Route-Access-Token"] = token
            request = httpx2.Request(
                method, f"http://testserver{path}", headers=headers, params=params, json=payload,
            )
            response = await _send(server_config, request)
            assert response.status_code == status, response.text
            assert response.headers["X-Request-ID"] == request_id
            assert ("X-Mock" in response.headers) == (mode_name == "mock")
            return response.json()

        for name, destination in (("coords", _DESTINATION), ("search", {"query": _SEARCH})):
            result = await check("POST", _RETURN, name, 200, payload={
                "request_id": f"a3-route-{name}", "festival_id": "fst_000001",
                "origin": _ORIGIN, "destination": destination,
            })
            assert result["route_status"] == "ready"
            assert "route_access_token" not in result
            route_id = result["route_request_id"]
            route_ids[name] = route_ids[f"{name}-lookup"] = route_id
            # Exercise the access logger with a valid synthetic token from the test store.
            records = real_routes.get_service()._records if mode_name == "real" else mock_routes.route_requests
            token = tokens[f"{name} token"] = records[route_id].access_token
            looked_up = await check(
                "GET", f"{_RETURN}/{route_id}", f"{name}-lookup", 200,
                token=token, params={"unused_token": token, "unused_query": _SEARCH},
            )
            assert "route_access_token" not in looked_up
            expected = "unavailable" if mode_name == "real" and name == "coords" else "ready"
            assert looked_up["route_status"] == expected

        crowd = await check("GET", _CROWD, "crowd", 200, params={"unused_key": _KEYS["SEOUL_OPEN_API_KEY"]})
        assert crowd["status"] == "ok"
        return tokens, route_ids

    tokens, route_ids = asyncio.run(exercise())
    forbidden = {"search term": _SEARCH, **tokens, **_KEYS}
    for endpoint, coordinates in (
        ("origin", _ORIGIN), ("destination", _DESTINATION), ("search result", _SEARCH_COORDINATES),
    ):
        for axis, value in coordinates.items():
            whole, fraction = str(value).split(".")
            for digits in range(4, len(fraction) + 1):
                label = f"{endpoint} {axis} ({digits} digits)"
                forbidden[f"{label} rounded"] = f"{value:.{digits}f}"
                forbidden[f"{label} truncated"] = f"{whole}.{fraction[:digits]}"
    _assert_no_raw_logs(capture.text, forbidden)

    request_logs = {
        record.getMessage().split(" request_id=", 1)[1]
        for record in capture.records if record.name == "uvicorn.error.api_requests"
    }
    statuses = {
        "coords": "ready", "coords-lookup": "unavailable" if mode_name == "real" else "ready",
        "search": "ready", "search-lookup": "ready", "crowd": "ok",
    }
    assert request_logs == {
        f"'a3-{mode_name}-{name}' http_status=200 result_status={status} route_request_id={route_ids[name]}"
        for name, status in statuses.items()
    }
    access_logs = [record for record in capture.records if record.name == "uvicorn.access"]
    assert len(access_logs) == 5
    assert all(record.getMessage().endswith(" 200") for record in access_logs)
    assert any("Started scope=" in record.getMessage()
               for record in capture.records if record.name == "uvicorn.asgi")
    if mode_name == "real":
        assert calls[:4] == [
            "/transit/routes", "/v2/routing/publictraffic", "/v2/local/search/keyword.json", "/transit/routes",
        ]
        assert calls[4:] and set(calls[4:]) == {"citydata_ppltn"}
    else:
        assert not calls


def test_a3_unexpected_error_keeps_envelope_without_raw_traceback(
    monkeypatch: pytest.MonkeyPatch, capture: pytest.LogCaptureFixture, server_config: Config,
) -> None:
    service = Mock()
    service.get_crowd = AsyncMock(side_effect=RuntimeError(_SEARCH))
    monkeypatch.setenv("CROWD_PROVIDER", "real")
    monkeypatch.setattr(seoul_crowd, "get_service", lambda: service)

    response = asyncio.run(_send(server_config, httpx2.Request(
        "GET", f"http://testserver{_CROWD}", headers={"X-Request-ID": "a3-error"},
    )))
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "a3-error"
    assert response.json()["error"] == {
        "code": "INTERNAL_SERVER_ERROR", "message": "서버에서 오류가 발생했습니다.",
        "request_id": "a3-error", "retryable": False,
    }
    _assert_no_raw_logs(capture.text, {"exception body": _SEARCH})
    assert "request_id='a3-error' http_status=500 error=INTERNAL_SERVER_ERROR" in capture.text


@pytest.mark.parametrize(("label", "raw"), [
    ("coordinate", "37.512347"),
    ("search term", _SEARCH),
    ("token", "rrt_fixture_control"),
    ("api key", _KEYS["SEOUL_OPEN_API_KEY"]),
])
def test_a3_detector_catches_deliberately_logged_raw_value(capture, label, raw) -> None:
    logging.getLogger("api.a3_control").warning("deliberately leaked %s", raw)
    with pytest.raises(pytest.fail.Exception, match=label):
        _assert_no_raw_logs(capture.text, {label: raw})


def test_a3_db_auth_keeps_ids_and_status_without_raw_credentials(
    monkeypatch: pytest.MonkeyPatch, capture: pytest.LogCaptureFixture, server_config: Config,
) -> None:
    from datetime import timezone
    from uuid import uuid4

    from api.auth import service, state, tokens
    from api.deps import CurrentUser, get_current_user

    signing_key = "fixture-auth-key-for-redaction-tests-only"
    password = "FixturePassword123"
    refresh = "fixture-refresh-secret-with-entropy"
    user_id = uuid4()
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("JWT_SECRET", signing_key)
    monkeypatch.setattr(state, "_auth_state", state.MemoryAuthState())
    access = tokens.issue_access_token(user_id, "user", datetime.now(timezone.utc), 1800)
    claims = tokens.read_access_token(f"Bearer {access}")

    def signup(body):
        if body.display_name == "Error":
            raise RuntimeError(body.password.get_secret_value())
        return {"user_id": str(user_id), "display_name": body.display_name, "is_mock": False}

    token_response = {"access_token": access, "refresh_token": refresh, "is_mock": False}
    monkeypatch.setattr(service, "signup", signup)
    monkeypatch.setattr(service, "login", lambda _: token_response)
    monkeypatch.setattr(service, "refresh", lambda _: token_response)
    monkeypatch.setattr(service, "logout", lambda *_: None)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: CurrentUser(claims, "user", True))
    signup_body = {
        "email": "logs@example.test", "password": password, "display_name": "Tester",
        "birth_year": 2000, "gender": "female",
    }

    async def exercise() -> None:
        cases = (
            ("signup", "signup", signup_body, 201),
            ("validation", "signup", {**signup_body, "gender": "invalid"}, 422),
            ("error", "signup", {**signup_body, "display_name": "Error"}, 500),
            ("login", "login", {"email": signup_body["email"], "password": password}, 200),
            ("refresh", "refresh", {"refresh_token": refresh}, 200),
            ("logout", "logout", {"refresh_token": refresh}, 204),
        )
        for label, endpoint, payload, status in cases:
            response = await _send(server_config, httpx2.Request(
                "POST", f"http://testserver/api/v1/auth/{endpoint}",
                headers={"X-Request-ID": f"a3-auth-{label}", "Authorization": f"Bearer {access}"},
                params={"unused_key": signing_key, "unused_token": refresh}, json=payload,
            ))
            assert response.status_code == status
            assert response.headers["X-Request-ID"] == f"a3-auth-{label}"
            assert "X-Mock" not in response.headers

    asyncio.run(exercise())
    _assert_no_raw_logs(capture.text, {
        "JWT signing key": signing_key, "password": password, "Access JWT": access, "Refresh token": refresh,
    })
    assert "request_id='a3-auth-login' http_status=200" in capture.text
    assert "request_id='a3-auth-error' http_status=500" in capture.text
    assert sum(record.name == "uvicorn.access" for record in capture.records) == 6
    assert any(record.name == "uvicorn.asgi" for record in capture.records)
