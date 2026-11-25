"""SEC-05: API를 DB 모드로 돌릴 때 앱 로그·화면 출력·응답에 비밀값이 남지 않는지 (R04 한태경).

오현님 A3 시험(`backend/tests/api/test_a3_log_redaction.py`)이 이미 요청 로그의 좌표·검색어·토큰과
공급원 키(TMAP·카카오·서울시·ROUTE_KEY_SECRET)를 모의·실제 모드에서 확인한다. 이 파일은 A3가 다루지 않는
**DB 비밀번호 3종**(`DB_USER_PASSWORD`·`DB_SERVICE_PASSWORD`·`DB_MIGRATION_DSN`)과 `DATA_GO_KR_SERVICE_KEY`를,
**DB 모드(`FESTIVAL_DATA=db`)에서 DB가 꺼졌을 때·비밀번호가 틀렸을 때·정상일 때** 확인한다.

검사 대상: 모든 로거(레벨 1 이상), 표준 출력·오류(stdout/stderr), API 응답 본문과 헤더.
- DB 꺼짐: DB 없이 실행 (닫힌 포트)
- 정상 조회·틀린 비밀번호: `DB_LIVE_TEST=1`과 일회용 DB 접속값(`DB_*`, `DB_MIGRATION_DSN`)이 필요
- 오현님 API 코드(`backend/api`, DB 모드 축제 조회)가 없으면 건너뜀(main 병합 전)
"""

import asyncio
import logging
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

BACKEND = Path(__file__).resolve().parents[2]
for path in (str(BACKEND), str(BACKEND.parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

LIVE = os.environ.get("DB_LIVE_TEST") == "1" and bool(os.environ.get("DB_MIGRATION_DSN"))
needs_live = pytest.mark.skipif(not LIVE, reason="DB_LIVE_TEST=1과 일회용 DB 접속값이 필요함")
SECRET_ENV = ("DB_USER_PASSWORD", "DB_SERVICE_PASSWORD", "DB_MIGRATION_DSN", "DATA_GO_KR_SERVICE_KEY")
FAKE_PROVIDER_KEYS = ("TMAP_APP_KEY", "KAKAO_REST_API_KEY", "SEOUL_OPEN_API_KEY", "ROUTE_KEY_SECRET")


def _marker(tag: str) -> str:
    return f"{tag}{secrets.token_hex(8)}"


def _app_modules():
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        from api.services import festival_store
    except Exception as exc:   # 의존성이나 API 코드가 없는 환경
        pytest.skip(f"API 코드를 불러올 수 없음: {exc}")
    return TestClient, app, festival_store


@pytest.fixture
def capture(caplog, capfd, monkeypatch):
    caplog.set_level(1)
    for name in ("api", "uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy", "sqlalchemy.engine", "psycopg", "httpx"):
        caplog.set_level(1, logger=name)
        monkeypatch.setattr(logging.getLogger(name), "propagate", True)

    def everything(responses) -> str:
        out, err = capfd.readouterr()
        bodies = "\n".join(f"{r.status_code} {dict(r.headers)} {r.text}" for r in responses)
        return "\n".join([caplog.text, "\n".join(r.getMessage() for r in caplog.records), out, err, bodies])
    return everything


def _exercise(client) -> list:
    """DB를 쓰는 축제 목록·상세와, DB와 무관한 모의 경로를 함께 부른다."""
    return [
        client.get("/api/v1/festivals", params={"page_size": 3}, headers={"X-Request-ID": "sec05-list"}),
        client.get("/api/v1/festivals/fst_01SEC05TEST0000000000000", headers={"X-Request-ID": "sec05-detail"}),
        client.get("/api/v1/festivals/fst_000001/crowd", headers={"X-Request-ID": "sec05-crowd"}),
    ]


def _assert_absent(text: str, secrets_by_name: dict[str, str]) -> None:
    leaked = [name for name, value in secrets_by_name.items() if value and value in text]
    assert not leaked, f"로그·출력·응답에 비밀값이 남음(이름만 표시): {leaked}"


def _set_secrets(monkeypatch, values: dict[str, str]) -> None:
    for name, value in values.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def db_mode(monkeypatch):
    TestClient, app, festival_store = _app_modules()
    from shared.db import session as sessions

    def close_user_engine():
        if sessions._user_engine.cache_info().currsize:
            try:
                asyncio.run(sessions._user_engine().dispose())
            finally:
                sessions._user_engine.cache_clear()

    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setenv("APP_ENV", "test")
    close_user_engine()
    try:
        yield TestClient, app, festival_store
    finally:
        # 공통 풀의 연결을 닫아 뒤의 원본 DB 복제 시험을 막지 않는다.
        close_user_engine()


def test_sec05_detector_sees_app_logs_and_stdout(capture, db_mode):
    """대조군: 앱 로거와 화면 출력에 일부러 남긴 값은 실제로 잡힌다(수집이 제대로 되는지)."""
    leaked_log, leaked_print = _marker("ctlLog"), _marker("ctlOut")
    logging.getLogger("api.sec05_control").warning("일부러 남긴 값 %s", leaked_log)
    print(leaked_print)
    with pytest.raises(AssertionError):
        _assert_absent(capture([]), {"log": leaked_log, "stdout": leaked_print})


def test_sec05_db_down_errors_do_not_expose_secrets(monkeypatch, capture, db_mode):
    TestClient, app, _ = db_mode
    values = {
        "DB_USER_PASSWORD": _marker("dbU"), "DB_SERVICE_PASSWORD": _marker("dbS"),
        "DATA_GO_KR_SERVICE_KEY": _marker("dgk"),
        **{name: _marker("pk") for name in FAKE_PROVIDER_KEYS},
    }
    migration_pw = _marker("dbM")
    values["DB_MIGRATION_DSN"] = f"postgresql://postgres:{migration_pw}@127.0.0.1:9/noldaga"
    _set_secrets(monkeypatch, values)
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "9")          # 닫힌 포트: DB가 꺼진 상황
    with TestClient(app, raise_server_exceptions=False) as client:
        responses = _exercise(client)
    assert responses[0].status_code >= 500 and responses[1].status_code >= 500   # DB 조회는 실패해야 시험 의미가 있음
    _assert_absent(capture(responses), {**values, "DB_MIGRATION_DSN 비밀번호": migration_pw})


@needs_live
def test_sec05_wrong_db_password_rejected_does_not_expose_it(monkeypatch, capture, db_mode):
    TestClient, app, _ = db_mode
    wrong = _marker("wrongU")
    monkeypatch.setenv("DB_USER_PASSWORD", wrong)
    with TestClient(app, raise_server_exceptions=False) as client:
        responses = _exercise(client)
    assert responses[0].status_code >= 500
    _assert_absent(capture(responses), {"틀린 DB_USER_PASSWORD": wrong})


@pytest.fixture
def published_festival():
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(os.environ["DB_MIGRATION_DSN"], autocommit=True) as db:
        db.execute("""INSERT INTO festivals (festival_id, title, region_code, category, source_class_level2, review_status, published_at, start_date, end_date)
                      VALUES ('fst_01SEC05TEST0000000000000', 'SEC-05 시험 축제(가상)', 'SEOUL', 'festival', 'EV01', 'approved', now(), current_date, current_date)""")
    yield
    with psycopg.connect(os.environ["DB_MIGRATION_DSN"], autocommit=True) as db:
        db.execute("DELETE FROM festivals WHERE festival_id = 'fst_01SEC05TEST0000000000000'")


@needs_live
def test_sec05_normal_db_requests_do_not_expose_real_db_secrets(capture, db_mode, published_festival):
    TestClient, app, _ = db_mode
    with TestClient(app, raise_server_exceptions=False) as client:
        responses = _exercise(client)
    assert responses[0].status_code == 200 and responses[0].json()["is_mock"] is False
    assert responses[1].status_code == 200
    real = {name: os.environ.get(name, "") for name in SECRET_ENV}
    real["DB_MIGRATION_DSN 비밀번호"] = urlsplit(os.environ["DB_MIGRATION_DSN"]).password or ""
    _assert_absent(capture(responses), real)
