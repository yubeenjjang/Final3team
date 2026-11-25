from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from api.main import app
from tests.routes.test_bus_crowding import BusRouteProvider, RETURN, TOKEN, evidence, source  # noqa: F401
from tests.routes.test_p18_route_store_db import (  # noqa: F401
    app_engine, body_for, festival_id, route_engine, use_db,
)
from tests.routes.test_p9_real_routes import Clock, FakeProvider

pytestmark = pytest.mark.db


def test_bus_selection_concurrency_tokens_rls_and_retention(
    route_engine, app_engine, festival_id, monkeypatch, source, use_user_db,
):
    calls, _ = source("success", delay=0.03)
    clock = Clock()
    use_db(
        route_engine, app_engine, monkeypatch, use_user_db, clock,
        BusRouteProvider("tmap", clock), FakeProvider("kakao", clock),
    )
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    with TestClient(app) as client:
        first = client.post(RETURN, json=body_for(festival_id))
        second = client.post(RETURN, json=body_for(festival_id))
        assert first.status_code == second.status_code == 200
        assert calls == []
        route_ids = [item.json()["route_request_id"] for item in (first, second)]
        headers = [{TOKEN: item.headers[TOKEN]} for item in (first, second)]

        def select(route_id, token):
            return client.get(f"{RETURN}/{route_id}", headers=token, params={"candidate_id": "c1"})

        assert select(route_ids[0], headers[1]).status_code == 403
        with ThreadPoolExecutor(max_workers=2) as pool:
            requests = [pool.submit(select, route_id, token) for route_id, token in zip(route_ids, headers)]
            selections = [request.result() for request in requests]
        assert all(item.status_code == 200 and evidence(item.json())["status"] == "available" for item in selections)
        assert calls == ["getStationByPos", "getStationByUid", "getArrInfoByRouteAll"]
        for route_id, token in zip(route_ids, headers):
            polled = client.get(f"{RETURN}/{route_id}", headers=token).json()
            assert evidence(polled)["status"] == "unverified"

        clock.now += timedelta(seconds=61)
        expired_match = select(route_ids[0], headers[0]).json()
        assert expired_match["completed_valid_route"] and evidence(expired_match)["status"] == "unknown"
        assert len(calls) == 3

    with route_engine.connect() as connection:
        candidates, stored_evidence = connection.execute(text("""
            SELECT candidates, evidence FROM public.route_results WHERE route_request_id = :id
        """), {"id": route_ids[0]}).one()
        assert {"lat", "lng"}.isdisjoint(candidates[0]["legs"][1]["stops"][0])
        assert candidates[0]["mode_evidence"]["bus_crowding"]["status"] == "unverified"
        assert "mode_evidence" not in stored_evidence
        assert connection.scalar(text("""
            SELECT bool_and(relrowsecurity) FROM pg_class
            WHERE oid IN ('public.route_requests'::regclass, 'public.route_results'::regclass)
        """))

    for table in ("route_requests", "route_results"):
        with pytest.raises(ProgrammingError) as error, app_engine.begin() as connection:
            connection.execute(
                text("SELECT set_config('app.user_id', :id, true)"), {"id": str(uuid4())},
            )
            connection.execute(
                text(f"SELECT 1 FROM public.{table} WHERE route_request_id = :id"), {"id": route_ids[0]},
            )
        assert error.value.orig.sqlstate == "42501"
