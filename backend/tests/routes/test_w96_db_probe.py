"""W96: latest A04/A05 DB path with a deterministic local route provider."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.providers.route_base import KST
from api.services import route_rate_limit
from tests.routes.test_p18_route_store_db import app_engine, festival_id, route_engine, use_db
from tests.routes.test_p9_real_routes import Clock, FakeProvider

pytestmark = pytest.mark.db


def test_w96_db_path_repeat_and_unique_complete(route_engine, app_engine, festival_id,
                                                monkeypatch, use_user_db):
    monkeypatch.setenv("ROUTE_RATE_LIMIT_PER_MIN", "10000")
    monkeypatch.setattr(route_rate_limit, "state", route_rate_limit.MemoryAuthState())
    clock = Clock(datetime.now(KST))
    tmap, kakao = FakeProvider("tmap", clock), FakeProvider("kakao", clock)
    use_db(route_engine, app_engine, monkeypatch, use_user_db, clock, tmap, kakao)

    def submit(client, index):
        started = time.monotonic()
        response = client.post("/api/v1/routes/return", json={
            "request_id": f"w96-{uuid4().hex}", "festival_id": festival_id,
            "destination": {"lat": 37.123456, "lng": round(126.789123 + index * 0.002, 6)},
        })
        payload = response.json()
        for _ in range(20):
            if response.status_code != 202 or payload.get("route_status") not in {"queued", "processing"}:
                break
            token = payload.get("route_access_token")
            assert token
            time.sleep(0.05)
            response = client.get(payload["status_url"], headers={"X-Route-Access-Token": token})
            payload = response.json()
        return response.status_code, payload.get("route_status"), payload.get("completed_valid_route"), (
            time.monotonic() - started) * 1000

    with TestClient(app) as client:
        for pattern, indices in (("repeat", [0] * 4), ("unique", list(range(1, 5)))):
            before = len(tmap.queries)
            with ThreadPoolExecutor(max_workers=4) as pool:
                rows = [future.result() for future in as_completed(
                    [pool.submit(submit, client, index) for index in indices]
                )]
            assert all(status == 200 and route_status == "ready" and valid is True
                       for status, route_status, valid, _ in rows)
            executions = len(tmap.queries) - before
            assert executions == (1 if pattern == "repeat" else 4)
            print(f"W96 DB {pattern}: offered=4 valid=4 provider_executions={executions} "
                  f"max_completion_ms={round(max(row[3] for row in rows), 2)}")
