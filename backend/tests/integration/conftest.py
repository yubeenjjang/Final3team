"""화면과 같은 ASGI 요청을 일회용 PostgreSQL에서 실행한다."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from uuid import UUID, uuid4

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth import state
from api.ingestion.festivals.normalize import KST
from api.main import app
from api.realtime import chat_socket
from api.services import assistant, festival_store
from shared.db import session as sessions


@pytest.fixture(scope="session")
def database_urls():
    if not all(os.environ.get(key, "").strip() for key in ("TEST_DB_URL", "TEST_DB_MIGRATION_URL")):
        pytest.skip("통합 시험에는 TEST_DB_URL과 TEST_DB_MIGRATION_URL이 모두 필요합니다.")
    owner_url = make_url(os.environ["TEST_DB_MIGRATION_URL"]).set(drivername="postgresql+psycopg")
    service_url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    template = owner_url.database
    if not template or template in {"postgres", "template0", "template1"} or service_url.database != template:
        pytest.fail("두 시험 URL은 001~026을 적용한 동일한 일회용 원본 DB를 지정해야 합니다.", pytrace=False)

    name = f"noldaga_itest_{uuid4().hex}"
    admin = create_engine(owner_url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True)
    quote = admin.dialect.identifier_preparer.quote_identifier
    try:
        try:
            with admin.connect() as db:
                db.exec_driver_sql(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(template)}")
        except OperationalError as error:
            state_code = getattr(error.orig, "sqlstate", None)
            pytest.fail(f"시험 DB 복제에 실패했습니다. 연결, CREATEDB 권한과 원본 DB의 연결 상태를 확인하세요. ({state_code})",
                        pytrace=False)
        try:
            yield owner_url.set(database=name), service_url.set(database=name)
        finally:
            with admin.connect() as db:
                db.exec_driver_sql(f"DROP DATABASE {quote(name)}")
    finally:
        admin.dispose()


def role_engine(engine: Engine, role: str) -> None:
    @event.listens_for(engine, "begin")
    def set_role(connection):
        connection.exec_driver_sql(f"SET LOCAL ROLE {role}")


@pytest.fixture
def service_db(database_urls) -> Iterator[Engine]:
    _, service_url = database_urls
    engine = create_engine(service_url, hide_parameters=True)
    role_engine(engine, "noldaga_service")
    try:
        yield engine
    finally:
        engine.dispose()


class Browser:
    def __init__(self, http: httpx.AsyncClient, sockets: TestClient):
        self.http = http
        self.sockets = sockets

    def run(self, function, *args, **kwargs):
        return self.sockets.portal.call(partial(function, *args, **kwargs))

    def request(self, method, path, **kwargs):
        return self.run(self.http.request, method, path, **kwargs)


@pytest.fixture
def browser(database_urls, service_db, monkeypatch) -> Iterator[Browser]:
    owner_url, _ = database_urls
    user_db = create_async_engine(owner_url, hide_parameters=True)
    catalog_db = create_engine(owner_url, hide_parameters=True, isolation_level="REPEATABLE READ")
    role_engine(user_db.sync_engine, "noldaga_app")
    role_engine(catalog_db, "noldaga_app")
    monkeypatch.setattr(sessions, "_service_engine", lambda: service_db)
    monkeypatch.setattr(sessions, "_user_engine", lambda: user_db)
    monkeypatch.setattr(festival_store, "get_festival_engine", lambda: catalog_db)
    for provider in ("AUTH_PROVIDER", "FESTIVAL_DATA", "ASSISTANT_PROVIDER"):
        monkeypatch.setenv(provider, "db")
    monkeypatch.setenv("JWT_SECRET", "offline-itest-signing-value-not-for-production")
    monkeypatch.setenv("JWT_ISSUER", "noldaga-itest")
    monkeypatch.setenv("ASSISTANT_TOKEN_SECRET", "offline-itest-assistant-value-not-for-production")
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MIN", "10")
    monkeypatch.setenv("ASSISTANT_RATE_LIMIT_PER_MIN", "10")
    monkeypatch.setattr(state, "_auth_state", state.MemoryAuthState())
    monkeypatch.setattr(assistant, "rate_limit", assistant.MemoryAssistantRateLimit())
    monkeypatch.setattr(chat_socket, "tickets", chat_socket.MemoryTickets())
    monkeypatch.setattr(chat_socket, "bus", chat_socket.MemoryChatBus())
    monkeypatch.setattr(chat_socket, "limits", chat_socket.MessageLimits())

    def unexpected_http(*args, **kwargs):
        pytest.fail("통합 시험 중 외부 HTTP 호출이 발생했습니다.", pytrace=False)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", unexpected_http)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", unexpected_http)
    try:
        with TestClient(app) as sockets:
            http = httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver", trust_env=False,
            )
            browser = Browser(http, sockets)
            try:
                yield browser
            finally:
                browser.run(http.aclose)
                browser.run(user_db.dispose)
    finally:
        catalog_db.dispose()


def checked(response: httpx.Response, status: int, code: str | None = None):
    assert response.status_code == status, (response.request.method, response.request.url.path,
                                            response.status_code)
    assert "X-Mock" not in response.headers
    if status == 204:
        assert response.content == b""
        return None
    body = response.json()
    if code is not None:
        assert body["error"]["code"] == code
    return body


def auth_header(login):
    return {"Authorization": f"Bearer {login['access_token']}"}


@dataclass(frozen=True, repr=False)
class Account:
    user_id: UUID
    credentials: dict[str, str]
    login: dict

    @property
    def headers(self):
        return auth_header(self.login)


@pytest.fixture
def register(browser, service_db):
    def create(*, operator: bool = False) -> Account:
        suffix = uuid4().hex[:10]
        credentials = {"email": f"itest-{suffix}@example.test", "password": "Fixture-Password123"}
        signup = checked(browser.request("POST", "/api/v1/auth/signup", json={
            **credentials, "display_name": suffix, "birth_year": 2000, "gender": "female",
        }), 201)
        assert signup["is_mock"] is False
        uid = UUID(signup["user_id"])
        if operator:
            with service_db.begin() as db:
                db.execute(text("UPDATE public.profiles SET role = 'operator' WHERE user_id = :uid"), {"uid": uid})
        login = checked(browser.request("POST", "/api/v1/auth/login", json=credentials), 200)
        assert login["user"] == {"user_id": str(uid), "display_name": suffix,
                                 "role": "operator" if operator else "user"}
        assert login["is_mock"] is False
        return Account(uid, credentials, login)

    return create


@pytest.fixture
def festivals(service_db):
    """TourAPI 응답은 공개 축제와 공개 조건을 각각 어기는 행으로 대체한다."""
    key = uuid4().hex[:12]
    today = datetime.now(KST).date()
    ids = {kind: f"fst_{key}{index}" for index, kind in enumerate(("public", "pending", "event"))}
    rows = [
        (ids["public"], "EV01", "approved", True),
        (ids["pending"], "EV01", "pending", False),
        (ids["event"], "EV03", "approved", True),
    ]
    with service_db.begin() as db:
        db.execute(text("""
            INSERT INTO public.festivals
                (festival_id, title, region_code, category, source_class_level2, review_status,
                 published_at, start_date, end_date, last_synced_at)
            VALUES (:id, :title, 'SEOUL', 'festival', :source_class, :status,
                    CASE WHEN :published THEN now() ELSE NULL END, :start, :end, now())
        """), [{"id": fid, "title": f"통합시험 {key}", "source_class": source_class, "status": status,
                "published": published, "start": today, "end": today + timedelta(days=3)}
               for fid, source_class, status, published in rows])
    return ids, key
