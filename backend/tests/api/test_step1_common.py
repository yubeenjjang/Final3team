import ast
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_HEALTH = "/api/v1/health"
_FESTIVALS = "/api/v1/festivals"
_REQUEST_ID = re.compile(r"req_[0-9A-Za-z]{26}")
_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request", "stream", "send"}
_NETWORK_CALLS = {
    "httpx": _HTTP_METHODS | {"Client", "AsyncClient", "HTTPTransport", "AsyncHTTPTransport"},
    "httpx2": _HTTP_METHODS | {"Client", "AsyncClient", "HTTPTransport", "AsyncHTTPTransport"},
    "requests": _HTTP_METHODS | {"Session", "session", "HTTPAdapter"},
    "requests.api": _HTTP_METHODS | {"session"},
    "requests.sessions": {"Session", "session"},
    "requests.adapters": {"HTTPAdapter"},
    "urllib.request": {"urlopen", "urlretrieve", "build_opener", "OpenerDirector"},
    "aiohttp": {"ClientSession", "TCPConnector", "UnixConnector", "request"},
    "aiohttp.client": {"ClientSession", "request"},
    "aiohttp.connector": {"TCPConnector", "UnixConnector"},
    "socket": {
        "socket", "SocketType", "create_connection", "create_server", "fromfd",
        "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo",
    },
}
_REAL_API_MODULES = {
    "providers/kakao.py", "providers/tmap.py", "providers/tourapi.py",
    "providers/seoul_citydata.py", "providers/quota.py", "providers/route_base.py",
    "providers/festival_source.py", "providers/kakao_places.py",
    "services/real_routes.py", "services/seoul_crowd.py", "services/festival_store.py",
}


def test_R1_openapi_and_health(client: TestClient) -> None:
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"] == {
        "title": "놀다가 API (mock)",
        "version": "0.1.0-mock",
    }
    assert {_HEALTH, _FESTIVALS, f"{_FESTIVALS}/{{festival_id}}"}.issubset(
        schema.json()["paths"]
    )
    health = client.get(_HEALTH)
    assert health.status_code == 200
    assert health.json()["is_mock"] is True


def test_R1_cors(client: TestClient) -> None:
    headers = (
        "x-request-id, x-route-access-token, x-run-access-token, "
        "x-mock-scenario, authorization"
    )
    for origin in ("http://localhost:3000", "http://localhost:5173"):
        preflight = client.options(
            _HEALTH,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": headers,
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["Access-Control-Allow-Origin"] == origin
        allowed = preflight.headers["Access-Control-Allow-Headers"].lower().split(", ")
        assert set(headers.split(", ")).issubset(allowed)

        response = client.get(_HEALTH, headers={"Origin": origin})
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert response.headers["Access-Control-Allow-Origin"] == origin
        assert response.headers["Access-Control-Expose-Headers"] == "X-Request-ID"

    response = client.get(_HEALTH, headers={"Origin": "http://localhost:3001"})
    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert "Access-Control-Allow-Origin" not in response.headers

    rejected = client.options(
        _HEALTH,
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert rejected.status_code == 400
    assert "Access-Control-Allow-Origin" not in rejected.headers
    assert rejected.json()["error"]["request_id"] == rejected.headers["X-Request-ID"]


def test_R1_store_starts_clean_before_mutation() -> None:
    from api.mocks.store import festivals

    assert len(festivals) == 6
    assert festivals["fst_000001"].name == "광화문 겨울빛 축제"
    festivals["fst_000001"].name = "시험에서 바꾼 이름"
    festivals.pop("fst_000006")


def test_R1_store_reset_restores_seed() -> None:
    from api.mocks.store import festivals, reset_store

    assert len(festivals) == 6
    assert festivals["fst_000001"].name == "광화문 겨울빛 축제"
    festivals["fst_000001"].name = "시험에서 바꾼 이름"
    festivals.clear()
    reset_store()
    assert len(festivals) == 6
    assert festivals["fst_000001"].name == "광화문 겨울빛 축제"


def test_R2_error_envelope(client: TestClient) -> None:
    for url, expected_status, expected_code in (
        (f"{_FESTIVALS}?region=MARS", 422, "VALIDATION_ERROR"),
        ("/api/v1/missing", 404, "NOT_FOUND"),
    ):
        response = client.get(url)
        assert response.status_code == expected_status
        body = response.json()
        assert set(body) == {"error"}
        assert "detail" not in body
        error = body["error"]
        assert set(error) == {"code", "message", "request_id", "retryable"}
        assert error["code"] == expected_code
        assert re.search("[가-힣]", error["message"])
        assert error["request_id"] == response.headers["X-Request-ID"]
        assert error["retryable"] is False
        if expected_status == 422:
            assert "region" in error["message"]


def test_R3_request_id_is_preserved(client: TestClient) -> None:
    for request_id in ("a", "web.MOCK-request/1", "a" * 64):
        response = client.get(_HEALTH, headers={"X-Request-ID": request_id})
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert response.headers["X-Request-ID"] == request_id


def test_R3_request_id_is_generated_for_missing_or_invalid_header(client: TestClient) -> None:
    for headers in ({}, {"X-Request-ID": ""}, {"X-Request-ID": "a" * 65}):
        response = client.get(_HEALTH, headers=headers)
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert _REQUEST_ID.fullmatch(response.headers["X-Request-ID"])


def test_R3_request_id_matches_error_header(client: TestClient) -> None:
    response = client.get(
        f"{_FESTIVALS}/abc", headers={"X-Request-ID": "mock-error-id"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["X-Request-ID"] == "mock-error-id"


def test_R4_mock_marker(client: TestClient) -> None:
    for url in (_HEALTH, _FESTIVALS, f"{_FESTIVALS}/fst_000001"):
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert response.headers["X-Mock"] == "true"

    missing = client.get("/api/v1/missing")
    assert missing.status_code == 404
    assert missing.headers["X-Mock"] == "true"


def _mock_api_sources(api_dir: Path) -> Iterator[Path]:
    for source in api_dir.rglob("*.py"):
        relative = source.relative_to(api_dir)
        if relative.parts[0] == "ingestion":
            continue  # CLI 수집과 증빙 적재
        if relative.as_posix() in _REAL_API_MODULES:
            continue  # DB·real 전용 구현과 공급원 어댑터. 모드 분기 라우터는 검사한다.
        yield source


def _call_path(expr: ast.expr) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return f"{_call_path(expr.value)}.{expr.attr}"
    return ""


def _network_calls(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update((entry.asname, entry.name) for entry in node.names if entry.asname)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            aliases.update(
                (entry.asname or entry.name, f"{node.module}.{entry.name}") for entry in node.names
            )
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            root, _, rest = _call_path(node.func).partition(".")
            path = ".".join(part for part in (aliases.get(root, root), rest) if part)
            module, _, member = path.rpartition(".")
            if member in _NETWORK_CALLS.get(module, ()):
                violations.append((node.lineno, path))
    return violations


def test_R5_no_external_calls() -> None:
    api_dir = Path(__file__).resolve().parents[2] / "api"
    violations = [
        f"{source.relative_to(api_dir)}:{line} {call}"
        for source in _mock_api_sources(api_dir)
        for line, call in _network_calls(source.read_text(encoding="utf-8"))
    ]
    assert not violations, f"모의 API에서 허용되지 않는 네트워크 호출 {violations}"


@pytest.mark.parametrize("code", [
    "import httpx\nhttpx.get(source_url)",
    "import httpx2 as http\nhttp.AsyncClient()",
    "from requests import Session as MakeSession\nMakeSession()",
    "from urllib import request as req\nreq.urlopen(source_url)",
    "import aiohttp\naiohttp.ClientSession()",
    "from aiohttp.client import ClientSession\nClientSession()",
    "import socket as net\nnet.create_connection(address)",
])
def test_R5_detects_network_calls_in_mock_code(code: str) -> None:
    assert _network_calls(code)


def test_R5_allows_urls_and_excludes_real_adapters(tmp_path: Path) -> None:
    sources = {
        "services/mock_example.py": (
            'from urllib.parse import urlsplit\nimport httpx\n'
            'source_url = "https://apis.data.go.kr/example"\nurlsplit(source_url)\n'
        ),
        "providers/tourapi.py": "import httpx\nhttpx.get(source_url)",
        "providers/mock_example.py": "import httpx\nhttpx.get(source_url)",
        "ingestion/tourapi_snapshot.py": 'source_url = "https://apis.data.go.kr/example"',
    }
    for name, code in sources.items():
        source = tmp_path / name
        source.parent.mkdir(exist_ok=True)
        source.write_text(code, encoding="utf-8")
    checked = {path.relative_to(tmp_path).as_posix() for path in _mock_api_sources(tmp_path)}
    assert checked == {"services/mock_example.py", "providers/mock_example.py"}
    assert not _network_calls(sources["services/mock_example.py"])
    assert _network_calls(sources["providers/mock_example.py"])


def test_R9_health_payload(client: TestClient) -> None:
    response = client.get(_HEALTH)
    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert response.json() == {
        "status": "ok",
        "db": "mock",
        "redis": "mock",
        "version": "0.1.0-mock",
        "is_mock": True,
    }


def test_R17_mock_doc() -> None:
    path = Path(__file__).resolve().parents[2] / "api" / "MOCK_API.md"
    content = path.read_text(encoding="utf-8")
    for title in ("실행", "시험", "A01", "A02", "A03", "가상 축제 6건"):
        assert f"## {title}" in content
    assert "모든 값은 가상" in content
    assert "`is_mock: true`" in content
    assert "uvicorn api.main:app --reload --port 8000" in content
    assert "python -m pytest backend/tests -q" in content
    for sequence in range(1, 7):
        assert f"| `fst_{sequence:06d}` |" in content
