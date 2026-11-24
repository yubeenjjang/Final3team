import json
import os
import time
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text

from api.ingestion.db import create_ingestion_engine
from api.main import app
from api.repositories.route_store import TOKEN_TTL, RouteStore, token_hash
from api.services import festival_store, real_routes
from shared.db import session as db_sessions
from tests.routes.test_p9_real_routes import Clock, FakeProvider, FakeQuota

pytestmark = pytest.mark.db
_RETURN = "/api/v1/routes/return"
_TOKEN = "X-Route-Access-Token"
_DB_FILES = Path(__file__).resolve().parents[3] / "Docs" / "Step 2" / "db"


@pytest.fixture
def route_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DB_URL")
    if not url:
        pytest.skip("일회용 DB의 TEST_DB_URL이 없습니다.")
    engine = create_ingestion_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def app_engine() -> Iterator[Engine]:
    url = os.environ.get("TEST_DB_APP_URL")
    if not url:
        pytest.skip("일회용 DB의 TEST_DB_APP_URL이 없습니다.")
    engine = create_engine(url, hide_parameters=True, isolation_level="REPEATABLE READ")
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT current_user = 'noldaga_app'")), (
                "TEST_DB_APP_URL에는 noldaga_app 계정이 필요합니다."
            )
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def festival_id(route_engine: Engine) -> Iterator[str]:
    festival_id = f"fst_{uuid4().hex[:20]}"
    with route_engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO public.festivals (festival_id, title, venue_name, region_code,
                                         latitude, longitude, published_at, review_status, start_date, end_date)
            VALUES (:id, :id, '합성 축제장', 'SEOUL', 37.500000, 127.000000, now(), 'approved', :today, :today)
        """), {"id": festival_id, "today": date.today()})
    try:
        yield festival_id
    finally:
        with route_engine.begin() as connection:
            connection.execute(text("""
                DELETE FROM public.route_results USING public.route_requests
                 WHERE route_results.route_request_id = route_requests.route_request_id
                   AND route_requests.festival_id = :id
            """), {"id": festival_id})
            connection.execute(text("DELETE FROM public.route_requests WHERE festival_id = :id"), {"id": festival_id})
            connection.execute(text("DELETE FROM public.festivals WHERE festival_id = :id"), {"id": festival_id})


def use_db(route_engine, app_engine, monkeypatch, clock, tmap, kakao):
    @event.listens_for(route_engine, "begin")
    def use_service_role(connection):
        connection.exec_driver_sql("SET LOCAL ROLE noldaga_service")

    monkeypatch.setattr(db_sessions, "_service_engine", lambda: route_engine)
    store = RouteStore()
    monkeypatch.setenv("ROUTE_PROVIDER", "real")
    monkeypatch.setenv("ROUTE_STORE", "db")
    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setenv("ROUTE_KEY_SECRET", "TEST_KEY_DO_NOT_USE")
    monkeypatch.setattr(festival_store, "get_festival_engine", lambda: app_engine)
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 0.4)

    def service():
        return real_routes.RealRouteService(
            tmap=lambda: tmap, kakao=lambda: kakao,
            quota=FakeQuota(),
            now=lambda: clock.now, store=store,
        )

    running_service = service()
    monkeypatch.setattr(real_routes, "get_service", lambda: running_service)
    return store, service


def body_for(festival_id):
    return {
        "request_id": f"synthetic-{uuid4().hex}", "festival_id": festival_id,
        "destination": {"lat": 37.123456, "lng": 126.789123},
    }


def test_P18_db_a02_a03_a04_a05_status_and_expiry(route_engine, app_engine, festival_id, monkeypatch):
    clock = Clock()
    tmap = FakeProvider("tmap", clock, gate=Event())
    _, new_service = use_db(route_engine, app_engine, monkeypatch, clock, tmap, FakeProvider("kakao", clock))
    body = body_for(festival_id)
    with TestClient(app) as client:
        listing = client.get("/api/v1/festivals", params={"q": festival_id}).json()
        assert listing["items"][0]["festival_id"] == festival_id
        assert client.get(f"/api/v1/festivals/{festival_id}").status_code == 200
        accepted = client.post(_RETURN, json=body)
        try:
            assert accepted.status_code == 202
            response = accepted.json()
            route_id = response["route_request_id"]
            url = response["status_url"]
            token = response["route_access_token"]
            headers = {_TOKEN: token}
            assert tmap.entered.wait(2)
            assert client.get(url).status_code == 401
            assert client.get(url, headers={_TOKEN: "synthetic-other"}).status_code == 403
            assert client.get(url, headers=headers).json()["route_status"] == "processing"
            same = client.post(_RETURN, json=body)
            assert same.status_code == 202 and same.json()["route_request_id"] == route_id
            assert client.post(_RETURN, json={**body, "travel_mode": "walk"}).status_code == 409
        finally:
            tmap.gate.set()

        # 같은 요청을 처리 중인 공급원과 무관한 새 서비스의 A05로 결과를 읽는다.
        with route_engine.connect() as connection:
            initial = connection.execute(text("""
                SELECT access_token_hash, request_body_hash, destination_place_hash, route_key
                FROM public.route_requests WHERE route_request_id = :id
            """), {"id": route_id}).one()
        assert initial.access_token_hash == token_hash(token)
        assert all(len(value) == 64 for value in initial)
        assert len(tmap.queries) == 1
        # 백그라운드 종료를 기다린다. 실제 시각 대신 시험 시계를 사용한다.
        deadline = time.monotonic() + 3
        while client.get(url, headers=headers).json()["route_status"] == "processing":
            assert time.monotonic() < deadline
            time.sleep(0.02)
        replacement = new_service()
        monkeypatch.setattr(real_routes, "get_service", lambda: replacement)
        ready = client.get(url, headers=headers).json()
        assert ready["route_status"] == "ready" and ready["completed_valid_route"]
        assert ready["provider"] == "tmap"
        assert ready["destination"] == {"type": "place"}
        assert "path" not in ready["route_candidates"][0]["legs"][0]
        replay = client.post(_RETURN, json=body).json()
        assert replay["route_access_token"] == token and replay["route_request_id"] == route_id

        with route_engine.begin() as connection:
            # 결과만 과거로 옮겨 토큰이 유효할 때의 만료 응답을 검증한다.
            connection.execute(text("""
                UPDATE public.route_results SET queried_at = :old WHERE route_request_id = :id
            """), {"old": clock.now - timedelta(hours=24), "id": route_id})
        expired = client.get(url, headers=headers).json()
        assert expired["route_status"] == "unavailable"
        assert expired["error"]["code"] == "ROUTE_RESULT_EXPIRED"
        assert expired["error"]["retryable"] is False
        assert expired["error"]["message"] == "경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요."
        assert "route_candidates" not in expired
        with route_engine.connect() as connection:
            purged = connection.execute(text("""
                SELECT candidates, evidence, purged_at FROM public.route_results WHERE route_request_id = :id
            """), {"id": route_id}).one()
        assert purged == (None, {}, clock.now)
        clock.now += TOKEN_TTL
        assert client.get(url, headers=headers).status_code == 401
        replay = client.post(_RETURN, json=body)
        assert replay.status_code == 200
        response = replay.json()
        assert response["route_request_id"] == route_id
        assert response["route_status"] == "unavailable"
        assert response["completed_valid_route"] is False
        assert response["error"]["code"] == "ROUTE_ACCESS_EXPIRED"
        assert response["error"]["retryable"] is False
        assert {"route_access_token", "route_candidates", "status_url"}.isdisjoint(response)
        assert client.post(_RETURN, json={**body, "travel_mode": "walk"}).status_code == 409
        assert len(tmap.queries) == 1


def test_P18_db_ready_request_without_restored_result(route_engine, app_engine, festival_id, monkeypatch):
    clock = Clock()
    use_db(route_engine, app_engine, monkeypatch, clock, FakeProvider("tmap", clock), FakeProvider("kakao", clock))
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 3)
    with TestClient(app) as client:
        submitted = client.post(_RETURN, json=body_for(festival_id))
        assert submitted.status_code == 200
        ready = submitted.json()
        assert ready["route_status"] == "ready"
        route_id = ready["route_request_id"]

        with route_engine.begin() as connection:
            # 012 백업에서 결과 데이터만 빠진 복원 상태를 재현한다.
            deleted = connection.execute(text("""
                DELETE FROM public.route_results WHERE route_request_id = :id
            """), {"id": route_id})
            assert deleted.rowcount == 1
            assert connection.scalar(text("""
                SELECT status FROM public.route_requests WHERE route_request_id = :id
            """), {"id": route_id}) == "ready"

        response = client.get(f"{_RETURN}/{route_id}", headers={_TOKEN: ready["route_access_token"]})
        assert response.status_code == 200
        restored = response.json()
        assert restored["route_status"] == "unavailable"
        assert restored["completed_valid_route"] is False
        assert restored["error"] == {
            "code": "ROUTE_RESULT_EXPIRED",
            "message": "경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요.",
            "retryable": False,
        }
        assert "route_candidates" not in restored


def test_P18_db_kakao_has_no_result_row(route_engine, app_engine, festival_id, monkeypatch):
    clock = Clock()
    use_db(route_engine, app_engine, monkeypatch, clock, FakeProvider("tmap", clock, error="temporary"),
           FakeProvider("kakao", clock))
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 3)
    with TestClient(app) as client:
        response = client.post(_RETURN, json=body_for(festival_id))
        assert response.status_code == 200 and response.json()["provider"] == "kakao"
        route = response.json()
        route_id = route["route_request_id"]
        status = client.get(f"{_RETURN}/{route_id}", headers={_TOKEN: route["route_access_token"]}).json()
    assert status["error"]["code"] == "ROUTE_SECONDARY_SYNC_ONLY"
    assert "route_candidates" not in status
    with route_engine.connect() as connection:
        row = connection.execute(text("""
            SELECT rq.status, rq.error_code, rs.route_request_id
            FROM public.route_requests rq LEFT JOIN public.route_results rs USING (route_request_id)
            WHERE rq.route_request_id = :id
        """), {"id": route_id}).one()
    assert row == ("unavailable", "ROUTE_SECONDARY_SYNC_ONLY", None)


def test_P18_db_sweeper_clears_cached_result_before_24h(route_engine, app_engine, festival_id, monkeypatch):
    clock = Clock()
    store, _ = use_db(route_engine, app_engine, monkeypatch, clock, FakeProvider("tmap", clock),
                      FakeProvider("kakao", clock))
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 3)
    with TestClient(app) as client:
        for _ in range(2):
            response = client.post(_RETURN, json=body_for(festival_id))
            assert response.status_code == 200 and response.json()["provider"] == "tmap"
        cached_id = response.json()["route_request_id"]
    clock.now += timedelta(hours=23)
    assert store.purge_expired(clock.now) >= 2
    with route_engine.connect() as connection:
        row = connection.execute(text("""
            SELECT source_type, candidates, evidence, validity_check, purged_at
            FROM public.route_results WHERE route_request_id = :id
        """), {"id": cached_id}).one()
    assert row == ("cache", None, {}, {}, clock.now)


def test_a3_db_route_rows_exclude_raw_places_before_and_after_purge(route_engine, festival_id, monkeypatch):
    clock = Clock()
    kakao = FakeProvider("kakao", clock)
    place_query = "synthetic-private-place"
    monkeypatch.setattr(kakao, "search_place", lambda query: (37.234512, 126.876512, place_query))
    store, _ = use_db(route_engine, route_engine, monkeypatch, clock, FakeProvider("tmap", clock), kakao)
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 3)
    point = {"lat": 37.123412, "lng": 126.789112}
    place = {"query": place_query}
    markers = ("37.1234", "126.7891", "37.2345", "126.8765", place_query)

    def check_stored_rows(route_ids, *, purged):
        with route_engine.connect() as connection:
            for route_id in route_ids:
                request, result = connection.execute(text("""
                    SELECT row_to_json(rq), row_to_json(rs)
                    FROM public.route_requests rq JOIN public.route_results rs USING (route_request_id)
                    WHERE rq.route_request_id = :id
                """), {"id": route_id}).one()
                assert len(request["origin_place_hash"] or "") == 64
                assert len(request["destination_place_hash"] or "") == 64
                assert (result["purged_at"] is not None) == purged
                assert bool(result["candidates"]) != purged
                for row in (request, result):
                    retained = json.dumps(row, ensure_ascii=False)
                    if any(raw in retained for raw in markers):
                        pytest.fail("경로 요청 또는 결과 행에 장소 원문이 저장됐습니다.", pytrace=False)

    route_ids = []
    with TestClient(app) as client:
        for origin, destination in ((point, place), (place, point)):
            body = {**body_for(festival_id), "origin": origin, "destination": destination}
            response = client.post(_RETURN, json=body)
            assert response.status_code == 200 and response.json()["provider"] == "tmap"
            route_ids.append(response.json()["route_request_id"])
    check_stored_rows(route_ids, purged=False)

    clock.now += timedelta(hours=23)
    assert store.purge_expired(clock.now) >= len(route_ids)
    check_stored_rows(route_ids, purged=True)


def test_P18_db_migration_011_up_down_up(route_engine):
    migration_url = os.environ.get("TEST_DB_MIGRATION_URL")
    engine = create_ingestion_engine(migration_url) if migration_url else route_engine
    try:
        with engine.connect() as connection:
            can_migrate = connection.execute(text("""
                SELECT pg_has_role(current_user, relowner, 'USAGE')
                  FROM pg_class WHERE oid = 'public.route_requests'::regclass
            """)).scalar_one()
            if not can_migrate:
                pytest.skip("011 DDL에는 테이블 소유자 권한 또는 TEST_DB_MIGRATION_URL이 필요합니다.")

            def has_token_column():
                return connection.execute(text("""
                    SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'
                                   AND table_name = 'route_requests' AND column_name = 'access_token_hash')
                """)).scalar_one()

            def apply(suffix):
                sql = (_DB_FILES / f"011_route_access_token{suffix}.sql").read_text()
                with connection.connection.driver_connection.cursor() as cursor:
                    cursor.execute(sql)

            if has_token_column():
                apply("_down")
            apply("")
            assert has_token_column()
            apply("_down")
            assert not has_token_column()
            apply("")
            assert has_token_column()
            connection.rollback()
    finally:
        if migration_url:
            engine.dispose()
