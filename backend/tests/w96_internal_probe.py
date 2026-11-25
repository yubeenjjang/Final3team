"""Measure the current return-route API with a deterministic in-process provider.

The API, rate-limit layer, route service, deduplication and cache are real code.
No external route provider is called. Results are local internal baselines only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from fastapi.testclient import TestClient

from api.main import app
from api.providers.route_base import KST, ProviderResult, make_candidate
from api.services import real_routes, route_rate_limit


class LocalProvider:
    def __init__(self, name: str, delay_s: float) -> None:
        self.name = name
        self.delay_s = delay_s
        self.calls = 0
        self.lock = Lock()

    def query(self, query):
        with self.lock:
            self.calls += 1
        time.sleep(self.delay_s)
        candidate = make_candidate(
            1, duration_min=16, distance_m=1800, walk_m=400, transfers=0, fare_krw=1550,
            legs=[{"mode": "bus", "duration_min": 16, "path": [query.origin, query.destination]}],
            service_running=True,
            bus_crowding={"status": "unsupported", "reason": "시험용 공급원"},
        )
        tier = "primary" if self.name == "tmap" else "secondary"
        return ProviderResult(self.name, tier, datetime.now(KST).isoformat(), [candidate], [])


class LocalQuota:
    def try_acquire(self, provider):
        return True


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    return sorted(values)[math.ceil(len(values) * 0.95) - 1]


def _one(client: TestClient, destination_index: int, *, festival_id: str) -> dict:
    destination = {"lat": 37.5, "lng": round(126.9 + destination_index * 0.002, 6)}
    body = {"request_id": uuid4().hex, "festival_id": festival_id, "destination": destination}
    started = time.monotonic()
    response = client.post("/api/v1/routes/return", json=body)
    post_ms = (time.monotonic() - started) * 1000
    payload = response.json()
    status = payload.get("route_status")
    polls = 0
    while response.status_code == 202 and status in {"queued", "processing"} and polls < 12:
        token = payload.get("route_access_token") or response.headers.get("X-Route-Access-Token")
        if not token:
            return {"http_status": response.status_code, "route_status": status,
                    "valid_completed": False, "error": "MISSING_ROUTE_TOKEN",
                    "post_ms": round(post_ms, 2),
                    "completion_ms": round((time.monotonic() - started) * 1000, 2), "polls": polls}
        time.sleep(0.05)
        response = client.get(payload.get("status_url") or f"/api/v1/routes/return/{payload['route_request_id']}",
                              headers={"X-Route-Access-Token": token})
        payload = response.json()
        status = payload.get("route_status")
        polls += 1
    return {
        "http_status": response.status_code, "route_status": status,
        "error": (payload.get("error") or {}).get("code"),
        "valid_completed": payload.get("completed_valid_route") is True and status == "ready",
        "post_ms": round(post_ms, 2),
        "completion_ms": round((time.monotonic() - started) * 1000, 2), "polls": polls,
    }


def _batch(client: TestClient, *, pattern: str, pacing: str, count: int, concurrency: int,
           festival_id: str, provider: LocalProvider) -> dict:
    before_calls = provider.calls
    destinations = [0 if pattern == "repeat" else index for index in range(count)]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = []
        for index in destinations:
            futures.append(pool.submit(_one, client, index, festival_id=festival_id))
            if pacing == "sustained":
                time.sleep(0.1)
        rows = [future.result() for future in as_completed(futures)]
    return {
        "offered": count, "unique_destinations": len(set(destinations)),
        "provider_executions": provider.calls - before_calls,
        "valid_completed": sum(row["valid_completed"] for row in rows),
        "rejected": sum(row["http_status"] in {429, 503} for row in rows),
        "errors": sum(bool(row["error"]) for row in rows),
        "unfinished": sum(row["route_status"] in {"queued", "processing"} for row in rows),
        "post_p95_ms": _p95([row["post_ms"] for row in rows]),
        "completion_p95_ms": _p95([row["completion_ms"] for row in rows]),
        "elapsed_s": round(time.monotonic() - started, 3),
        "statuses": {status: sum(row["route_status"] == status for row in rows)
                     for status in sorted({row["route_status"] for row in rows if row["route_status"]})},
    }


def run_probe(*, count: int = 8, concurrency: int = 4, delay_s: float = 0.05,
              festival_id: str = "fst_000001") -> dict:
    if not 1 <= count <= 20 or not 1 <= concurrency <= 8 or not 0 <= delay_s <= 0.5:
        raise ValueError("요청 수 1~20, 동시 실행 1~8, 공급원 지연 0~0.5초가 필요합니다")
    original_env = {name: os.environ.get(name) for name in
                    ("ROUTE_PROVIDER", "ROUTE_STORE", "ROUTE_RATE_LIMIT_PER_MIN", "FESTIVAL_DATA")}
    original_service = real_routes.get_service
    original_state = route_rate_limit.state
    rows = []
    try:
        os.environ.update(ROUTE_PROVIDER="real", ROUTE_STORE="memory", ROUTE_RATE_LIMIT_PER_MIN="10000",
                          FESTIVAL_DATA="mock")
        route_rate_limit.state = route_rate_limit.MemoryAuthState()
        for pattern in ("repeat", "unique"):
            for pacing in ("burst", "sustained"):
                provider = LocalProvider("tmap", delay_s)
                secondary = LocalProvider("kakao", delay_s)
                service = real_routes.RealRouteService(tmap=lambda: provider, kakao=lambda: secondary,
                                                       quota=LocalQuota())
                real_routes.get_service = lambda: service
                with TestClient(app) as client:
                    for cache_state in ("cold", "warm"):
                        result = _batch(client, pattern=pattern, pacing=pacing, count=count,
                                        concurrency=concurrency, festival_id=festival_id, provider=provider)
                        rows.append({"pattern": pattern, "pacing": pacing, "cache_state": cache_state,
                                     **result})
    finally:
        real_routes.get_service = original_service
        route_rate_limit.state = original_state
        for name, value in original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    return {
        "run_id": "w96_" + uuid4().hex[:16],
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_real_route_api_simulated_provider",
        "settings": {"count": count, "concurrency": concurrency, "provider_delay_s": delay_s,
                     "festival_id": festival_id, "rate_limit_per_min": 10000},
        "limitations": "실제 API 내부 경로를 측정했지만 공급원은 시험용이며 DB 저장·외부 네트워크·운영 부하는 포함하지 않음",
        "scenarios": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--delay-s", type=float, default=0.05)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_probe(count=args.count, concurrency=args.concurrency, delay_s=args.delay_s)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"W96 내부 API 계측 결과 저장: {args.output}")


if __name__ == "__main__":
    main()
