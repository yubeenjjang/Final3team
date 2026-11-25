import asyncio
import logging
import os
from dataclasses import replace
from datetime import datetime, timedelta
from inspect import isawaitable
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url

from api.main import app
from api.providers import festival_source, traffic_incidents
from api.providers.festival_source import FestivalSource
from api.providers.route_base import KST
from api.services import real_festival_info

_NOW = datetime(2026, 11, 19, 17, 23, tzinfo=KST)
_POLICE = "https://apis.data.go.kr/fixture/incident"
_FILES = Path(__file__).with_name("fixtures")
_SYNTHETIC_KEY = "fixture+traffic/test="


def _url(festival="fst_000001", endpoint="traffic-incidents"):
    return f"/api/v1/festivals/{festival}/{endpoint}"


@pytest.fixture
def upstream(monkeypatch, tmp_path):
    monkeypatch.setenv("TRAFFIC_INCIDENT_PROVIDER", "real")
    monkeypatch.setenv("POLICE_INCIDENT_API_URL", _POLICE)
    for key in ("DATA_GO_KR_SERVICE_KEY", "SEOUL_OPEN_API_KEY", "UTIC_API_KEY"):
        monkeypatch.setenv(key, "fixture%2Btraffic%2Ftest%3D")
    monkeypatch.setenv("FESTIVAL_INFO_QUOTA_FILE", str(tmp_path / "quota.json"))
    monkeypatch.setattr(festival_source, "_RETRY_DELAY_S", 0)
    for env in ("FESTIVAL_DATA", "UTIC_ENABLED", "UTIC_REFRESH_S", "UTIC_TIMEOUT_S", "VISIT_FORECAST_MAPPING_FILE"):
        monkeypatch.delenv(env, raising=False)

    calls = []
    clocks = {"wall": _NOW, "monotonic": 0}

    def configure(**replies):
        async def handler(request):
            provider = {
                "apis.data.go.kr": "police", "www.utic.go.kr": "utic", "openapi.seoul.go.kr": "topis",
            }[request.url.host]
            calls.append(provider)
            # 요청이 여러 개 겹칠 수 있게 전송 중 이벤트 루프에 제어권을 넘깁니다.
            await asyncio.sleep(0)
            if provider == "topis":
                assert request.url.path == f"/{_SYNTHETIC_KEY}/xml/AccInfo/1/1000/"
            else:
                param = "serviceKey" if provider == "police" else "key"
                assert request.url.params[param] == _SYNTHETIC_KEY
                if provider == "police":
                    assert request.url.params["numOfRows"] == "1000"
            reply = replies[provider]
            if callable(reply):
                result = reply(request)
                return await result if isawaitable(result) else result
            return httpx2.Response(200, content=(_FILES / reply).read_bytes())

        service = real_festival_info.FestivalInfoService(FestivalSource(
            transport=httpx2.MockTransport(handler),
            now=lambda: clocks["wall"], clock=lambda: clocks["monotonic"],
        ))
        monkeypatch.setattr(real_festival_info, "get_service", lambda: service)
        return calls, clocks

    return configure


def test_traffic_default_mock_and_validation(upstream, monkeypatch):
    monkeypatch.delenv("TRAFFIC_INCIDENT_PROVIDER")
    calls, _ = upstream()
    with TestClient(app) as client:
        response = client.get(_url())
        assert response.headers["X-Mock"] == "true"
        assert response.json()["items"][0]["type"] == "control"
        assert client.get(_url(), params={"type": "construction"}).json()["items"] == []
        assert client.get(_url(), params={"radius_m": 499}).status_code == 422
        assert client.get(_url(), params={"radius_m": 10001}).status_code == 422
        assert client.get(_url(), params={"type": "weather"}).status_code == 422
        assert client.get(_url("unknown")).status_code == 422
        assert client.get(_url("fst_999999")).status_code == 404
        assert client.get(_url("fst_000006")).json()["error"]["code"] == "FESTIVAL_LOCATION_UNKNOWN"
    assert calls == []


def test_traffic_filters_merges_and_caches_national_and_seoul_feeds(upstream):
    calls, clocks = upstream(police="police_traffic_synthetic.xml", topis="seoul_topis_traffic_synthetic.xml")
    with TestClient(app) as client:
        response = client.get(_url())
        assert "X-Mock" not in response.headers
        body = response.json()
        assert body["is_mock"] is False and body["status"] == "ok"
        assert body["observed_at"] == "2026-11-19T17:23:00+09:00"
        assert body["coverage"] == {"scope": "national", "region_code": "SEOUL", "supported": True}
        assert [(item["source"], item["type"]) for item in body["items"]] == [
            ("police_incident", "accident"), ("seoul_topis", "accident"), ("police_incident", "construction"),
        ]
        first, second, work = body["items"]
        assert second["title"] == "세종대로 별도 고장 차량"
        assert first["start_at"] == "2026-11-19T17:15:00+09:00"
        assert second["end_at"] == "2026-11-19T19:30:00+09:00"
        assert (second["lat"], second["lng"]) == pytest.approx((37.5765, 126.9771), abs=0.000001)
        assert first["distance_m"] < second["distance_m"] < 100 < work["distance_m"]
        assert client.get(_url(), params={"radius_m": 500, "type": "construction"}).json()["items"] == []
        (busan,) = client.get(_url("fst_000003"), params={"type": "event"}).json()["items"]
        assert busan["distance_m"] == 0 and busan["end_at"] is None
        assert sorted(calls) == ["police", "topis"]
        clocks["wall"] += timedelta(seconds=121)
        assert client.get(_url()).json()["error"]["code"] == "SOURCE_STALE"
        clocks["monotonic"] = 60
        assert client.get(_url()).json()["status"] == "ok"
    assert sorted(calls) == ["police", "police", "topis", "topis"]


def test_traffic_merge_requires_distance_time_and_shared_event_evidence():
    start = _NOW - timedelta(minutes=10)
    end = _NOW + timedelta(minutes=10)
    original = traffic_incidents.Incident(
        "accident", "사고 1", 37.5759, 126.9771, start, end, "police_incident", "1000000100",
    )
    peer = replace(original, source="seoul_topis", lat=37.5767)
    first = traffic_incidents.IncidentReading("police_incident", _NOW, [original])

    def count(item):
        second = traffic_incidents.IncidentReading("seoul_topis", _NOW, [item])
        return len(traffic_incidents.nearby_incidents([first, second], (37.5759, 126.9771), 2000, None))

    assert count(peer) == 1
    assert count(replace(peer, lat=37.5769)) == 2
    assert count(replace(peer, start_at=end + timedelta(seconds=1), end_at=None)) == 2
    assert count(replace(peer, title="별도 사고", link_id=None)) == 2
    assert count(replace(peer, start_at=None)) == 2


def test_traffic_topis_only_when_utic_is_disabled(upstream, monkeypatch):
    monkeypatch.delenv("POLICE_INCIDENT_API_URL")
    worker = AsyncMock()
    monkeypatch.setattr(traffic_incidents, "refresh_utic", worker)
    calls, _ = upstream(topis="seoul_topis_traffic_synthetic.xml")
    with TestClient(app) as client:
        seoul = client.get(_url()).json()
        assert seoul["coverage"]["scope"] == "seoul_only"
        assert seoul["source"] == "seoul_topis" and seoul["notices"]
        busan = client.get(_url("fst_000003")).json()
        assert busan["status"] == "unavailable" and busan["error"]["retryable"] is False
    worker.assert_not_called()
    assert calls == ["topis"]


def test_traffic_reads_only_fresh_utic_snapshots_from_lifespan(upstream, monkeypatch):
    monkeypatch.delenv("POLICE_INCIDENT_API_URL")
    monkeypatch.setenv("UTIC_ENABLED", "true")

    async def check():
        started, release, saved = asyncio.Event(), asyncio.Event(), asyncio.Event()
        tasks = []

        class ObservedStore(traffic_incidents.MemoryUticSnapshotStore):
            async def save(self, reading):
                await super().save(reading)
                saved.set()

        async def utic_reply(request):
            tasks.append(asyncio.current_task())
            assert request.extensions["timeout"]["read"] == 20
            started.set()
            await release.wait()
            return httpx2.Response(200, content=(_FILES / "utic_traffic.xml").read_bytes())

        monkeypatch.setattr(traffic_incidents, "MemoryUticSnapshotStore", ObservedStore)
        calls, clocks = upstream(topis="seoul_topis_traffic_synthetic.xml", utic=utic_reply)
        async with app.router.lifespan_context(app) as state:
            async def api_with_state(scope, receive, send):
                await app({**scope, "state": state.copy()}, receive, send)

            await asyncio.wait_for(started.wait(), 2)
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(api_with_state), base_url="http://test",
            ) as client:
                async def read():
                    response = await asyncio.wait_for(client.get(_url(), params={"radius_m": 10000}), 2)
                    assert response.status_code == 200
                    return response.json()

                fallback = await read()
                assert fallback["source"] == "seoul_topis"
                assert fallback["coverage"]["scope"] == "seoul_only"
                assert fallback["notices"] == ["전국 교통 돌발을 확인할 수 없어 서울 TOPIS 정보만 표시해요."]

                release.set()
                await asyncio.wait_for(saved.wait(), 2)
                clocks["wall"] += timedelta(seconds=2 * traffic_incidents.INCIDENT_TTL_S)
                fresh = await read()
                assert (fresh["status"], fresh["coverage"]["scope"], fresh["source"]) == (
                    "ok", "national", "police_incident",
                )
                (police,) = [item for item in fresh["items"] if item["source"] == "police_incident"]
                assert police["start_at"] == "2026-11-19T16:56:00+09:00"

                clocks["wall"] += timedelta(seconds=1)
                clocks["monotonic"] += traffic_incidents.INCIDENT_TTL_S
                expired = await read()
                assert expired["status"] == "ok" and expired["source"] == fallback["source"]
                assert expired["items"] == fallback["items"] and expired["notices"] == fallback["notices"]
                assert calls == ["utic", "topis", "topis"]
        (worker,) = tasks
        assert worker.get_name() == "utic-refresh" and worker.cancelled()

    asyncio.run(check())


def test_utic_failed_refresh_keeps_last_success_and_logs_once(upstream, monkeypatch, caplog):
    monkeypatch.setenv("UTIC_ENABLED", "true")
    monkeypatch.setenv("UTIC_REFRESH_S", "0.01")
    monkeypatch.setenv("UTIC_TIMEOUT_S", "0.1")
    caplog.set_level(logging.DEBUG)
    raw_message = "합성 UTIC 원문"

    async def check():
        pending, cancelled = asyncio.Event(), asyncio.Event()
        timeouts = []

        async def utic_reply(request):
            timeouts.append(request.extensions["timeout"]["read"])
            logging.getLogger("httpx2").debug("request url %s", request.url)
            if len(timeouts) == 1:
                return httpx2.Response(200, content=(_FILES / "utic_traffic.xml").read_bytes())
            if len(timeouts) == 2:
                clocks["wall"] += timedelta(seconds=1)
                return httpx2.Response(200, text=(
                    f"<result><record><resultCode>02</resultCode><resultMsg>{raw_message} {_SYNTHETIC_KEY}"
                    "</resultMsg></record></result>"
                ))
            if len(timeouts) == 3:
                raise httpx2.ReadTimeout(str(request.url), request=request)
            pending.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        calls, clocks = upstream(utic=utic_reply)
        async with app.router.lifespan_context(app) as state:
            await asyncio.wait_for(pending.wait(), 2)
            reading = await state["utic_store"].read()
            assert reading.items and reading.observed_at == _NOW
            assert calls == ["utic"] * 4 and timeouts == [0.1] * 4
        assert cancelled.is_set()

    asyncio.run(check())
    warnings = [record for record in caplog.records if record.name == traffic_incidents.__name__]
    assert len(warnings) == 1 and warnings[0].exc_info is None
    for secret in (raw_message, _SYNTHETIC_KEY, "fixture%2Btraffic%2Ftest%3D"):
        assert secret not in caplog.text


@pytest.mark.parametrize("scenario,expected", [
    ("timeout", (2, "SOURCE_HTTP_ERROR", True)),
    ("quota_xml", (1, "SOURCE_RESULT_ERROR", False)),
    ("dtd", (1, "SOURCE_RESULT_ERROR", False)),
    ("empty", (1, None, None)),
])
def test_traffic_provider_errors_and_log_redaction(upstream, monkeypatch, caplog, scenario, expected):
    caplog.set_level(logging.DEBUG)
    monkeypatch.delenv("SEOUL_OPEN_API_KEY")

    def reply(request):
        logging.getLogger("httpx2").debug("request url %s", request.url)
        if scenario == "timeout":
            raise httpx2.ReadTimeout(str(request.url), request=request)
        payload = {
            "quota_xml": "<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>22</returnReasonCode>"
            "</cmmMsgHeader></OpenAPI_ServiceResponse>",
            "dtd": '<!DOCTYPE result [<!ENTITY unexpected "malformed">]><result>&unexpected;</result>',
            "empty": "<response><header><resultCode>03</resultCode></header></response>",
        }[scenario]
        return httpx2.Response(200, text=payload)

    calls, _ = upstream(police=reply)
    with TestClient(app) as client:
        response = client.get(_url())
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    count, code, retryable = expected
    assert len(calls) == count
    if code is None:
        assert body["status"] == "ok" and body["error"] is None
    else:
        assert body["status"] == "unavailable"
        assert (body["error"]["code"], body["error"]["retryable"]) == (code, retryable)
    for key in (_SYNTHETIC_KEY, "fixture%2Btraffic%2Ftest%3D"):
        assert key not in response.text and key not in caplog.text


def test_traffic_concurrent_requests_share_a_fetch(upstream):
    calls, _ = upstream(police="police_traffic_synthetic.xml", topis="seoul_topis_traffic_synthetic.xml")

    async def get():
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app), base_url="http://test") as client:
            return await asyncio.gather(*(client.get(_url()) for _ in range(12)))

    results = asyncio.run(get())
    assert all(result.status_code == 200 and result.json() == results[0].json() for result in results)
    assert sorted(calls) == ["police", "topis"]


@pytest.mark.db
def test_traffic_and_forecast_only_use_public_ev01_festivals_under_rls(upstream, monkeypatch, use_user_db):
    admin_url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or admin_url).set(drivername="postgresql+psycopg")
    admin = create_engine(admin_url, hide_parameters=True)
    public = create_engine(app_url, hide_parameters=True, isolation_level="REPEATABLE READ")
    if not os.environ.get("TEST_DB_APP_URL"):
        event.listen(public, "begin", lambda conn: conn.exec_driver_sql("SET LOCAL ROLE noldaga_app"))
    calls, _ = upstream(police="police_traffic_synthetic.xml")
    use_user_db(app_url, role=None if os.environ.get("TEST_DB_APP_URL") else "noldaga_app")
    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("VISIT_FORECAST_PROVIDER", "real")
    ids = [f"fst_{uuid4().hex[:20]}" for _ in range(3)]
    try:
        with admin.begin() as db:
            db.execute(text("""
                INSERT INTO public.festivals (
                  festival_id, title, region_code, category, source_class_level2,
                  latitude, longitude, review_status, published_at
                )
                VALUES (:open, '공개 축제', 'BUSAN', 'festival', 'EV01', 35.1003, 129.0337, 'approved', now()),
                       (:hidden, '검토 중', 'BUSAN', 'festival', 'EV01', 35.1003, 129.0337, 'pending', NULL),
                       (:event, '공연', 'BUSAN', 'festival', 'EV02', 35.1003, 129.0337, 'approved', now())
            """), dict(zip(("open", "hidden", "event"), ids)))
        with public.begin() as db:
            assert db.scalar(text("SELECT current_user")) == "noldaga_app"
            visible = db.scalars(text("SELECT festival_id FROM public.festivals WHERE festival_id = ANY(:ids)"),
                                 {"ids": ids}).all()
            assert visible == ids[:1]

        async def get():
            async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app), base_url="http://test") as client:
                return await asyncio.gather(
                    *(client.get(_url(ids[0])) for _ in range(6)),
                    *(client.get(_url(festival_id, path)) for festival_id in ids[1:]
                      for path in ("traffic-incidents", "visit-forecast")),
                )

        results = asyncio.run(get())
        assert [result.status_code for result in results] == [200] * 6 + [404] * 4
        assert [result.json()["items"][0]["type"] for result in results[:6]] == ["event"] * 6
        assert calls == ["police"]
    finally:
        with admin.begin() as db:
            db.execute(text("DELETE FROM public.festivals WHERE festival_id = ANY(:ids)"), {"ids": ids})
        public.dispose()
        admin.dispose()
