"""W96 예비 계측: 로컬 모의 귀가 API만 호출합니다.

실행 예: python -m backend.tests.route_load_probe --output /tmp/w96-mock.json
실제 공급원 성능·캐시 효과의 증빙으로 사용하지 않습니다.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4


MOCK_SCENARIOS = ("async_ready", "async_unavailable", "async_timeout", "overloaded")
MAX_REQUESTS = 20
MAX_CONCURRENCY = 8
MAX_POLLS = 5


def _fetch(request: Request, timeout_s: float) -> tuple[int, dict[str, str], dict]:
    try:
        with urlopen(request, timeout=timeout_s) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, json.load(response)
    except HTTPError as error:
        try:
            body = json.load(error)
        except (ValueError, OSError):
            body = {}
        return error.code, {key.lower(): value for key, value in error.headers.items()}, body


def _mock_server(base_url: str, timeout_s: float) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username or parsed.password:
        raise ValueError("예비 부하 시험은 로컬 HTTP 모의 서버에서만 실행합니다")
    if parsed.path.rstrip("/") != "/api/v1" or parsed.query or parsed.fragment:
        raise ValueError("API 주소는 http://127.0.0.1:<port>/api/v1 형식이어야 합니다")
    status, headers, body = _fetch(Request(base_url + "/health"), timeout_s)
    if status != 200 or headers.get("x-mock") != "true" or body.get("is_mock") is not True:
        raise ValueError("모의 서버 확인에 실패하여 부하 요청을 중단했습니다")


def _one_route(base_url: str, festival_id: str, destination: str, mock_scenario: str, timeout_s: float, poll_s: float) -> dict:
    request_id = str(uuid4())
    payload = {
        "request_id": request_id,
        "festival_id": festival_id,
        "destination": {"query": destination},
    }
    request = Request(
        base_url + "/routes/return",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": "req_" + uuid4().hex[:26],
            "X-Mock-Scenario": mock_scenario,
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        status, headers, body = _fetch(request, timeout_s)
        post_ms = round((time.monotonic() - started) * 1000, 2)
        if headers.get("x-mock") != "true":
            return {"http_status": status, "error_code": "NON_MOCK_RESPONSE", "post_ms": post_ms}
        if status not in {200, 202}:
            error = body.get("error") or {}
            return {"http_status": status, "error_code": error.get("code", "HTTP_ERROR"), "post_ms": post_ms}
        if body.get("is_mock") is not True:
            return {"http_status": status, "error_code": "NON_MOCK_RESPONSE", "post_ms": post_ms}

        route_id = body.get("route_request_id")
        token = body.get("route_access_token")
        route_status = body.get("route_status")
        valid = body.get("completed_valid_route") is True and route_status == "ready"
        polls = 0
        # 202는 접수일 뿐이므로, 실제 ready와 유효 경로 여부까지 따로 확인합니다.
        while status == 202 and route_status in {"queued", "processing"} and polls < MAX_POLLS:
            if not isinstance(route_id, str) or not isinstance(token, str):
                return {"http_status": status, "error_code": "MISSING_ROUTE_TOKEN", "post_ms": post_ms}
            time.sleep(poll_s)
            poll_request = Request(
                base_url + "/routes/return/" + route_id,
                headers={"X-Route-Access-Token": token, "X-Request-ID": "req_" + uuid4().hex[:26]},
            )
            poll_status, poll_headers, poll_body = _fetch(poll_request, timeout_s)
            polls += 1
            if poll_headers.get("x-mock") != "true" or poll_body.get("is_mock") is not True:
                return {"http_status": poll_status, "error_code": "NON_MOCK_RESPONSE", "post_ms": post_ms}
            if poll_status != 200:
                error = poll_body.get("error") or {}
                return {"http_status": poll_status, "error_code": error.get("code", "POLL_ERROR"), "post_ms": post_ms}
            route_status = poll_body.get("route_status")
            valid = poll_body.get("completed_valid_route") is True and route_status == "ready"
        return {
            "http_status": status,
            "route_status": route_status,
            "valid_completed": valid,
            "post_ms": post_ms,
            "completion_ms": round((time.monotonic() - started) * 1000, 2),
            "polls": polls,
        }
    except (OSError, TimeoutError, URLError):
        return {"error_code": "CONNECTION_ERROR", "post_ms": round((time.monotonic() - started) * 1000, 2)}


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * 0.95) - 1]


def _summarize(name: str, destinations: list[str], rows: list[dict], elapsed_s: float) -> dict:
    statuses = Counter(row.get("route_status") or row.get("error_code") or "unknown" for row in rows)
    return {
        "scenario": name,
        "offered": len(rows),
        "unique_destinations": len(set(destinations)),
        "destination_repeat_ratio": round(1 - len(set(destinations)) / len(destinations), 3),
        "accepted_202": sum(row.get("http_status") == 202 for row in rows),
        "completed_200_at_submit": sum(row.get("http_status") == 200 for row in rows),
        "valid_completed": sum(row.get("valid_completed") is True for row in rows),
        "terminal_failed": sum(row.get("route_status") in {"unavailable", "timed_out", "rejected"} for row in rows),
        "unfinished_after_poll_limit": sum(row.get("route_status") in {"queued", "processing"} for row in rows),
        "rejected": sum(row.get("http_status") in {429, 503} or row.get("route_status") == "rejected" for row in rows),
        "statuses": dict(statuses),
        "post_p95_ms": _p95([row["post_ms"] for row in rows if "post_ms" in row]),
        "completion_p95_ms": _p95([row["completion_ms"] for row in rows if "completion_ms" in row]),
        "elapsed_s": round(elapsed_s, 3),
    }


def run_probe(base_url: str, festival_id: str, count: int, concurrency: int, poll_s: float, timeout_s: float) -> dict:
    if (not 1 <= count <= MAX_REQUESTS or not 1 <= concurrency <= MAX_CONCURRENCY
            or not math.isfinite(poll_s) or poll_s < 0.05
            or not math.isfinite(timeout_s) or timeout_s <= 0):
        raise ValueError("요청 수 1~20, 동시 실행 1~8, 조회 간격 0.05초 이상, 양의 시간 제한이 필요합니다")
    base_url = base_url.rstrip("/")
    _mock_server(base_url, timeout_s)
    started_at = datetime.now(timezone.utc).isoformat()
    scenarios = []
    for pattern in ("repeat", "unique"):
        destinations = ["서울역" if pattern == "repeat" else f"서울역 {index + 1}" for index in range(count)]
        for pacing in ("burst", "sustained"):
            for mock_scenario in MOCK_SCENARIOS:
                started = time.monotonic()
                futures = []
                with ThreadPoolExecutor(max_workers=concurrency) as pool:
                    for destination in destinations:
                        futures.append(pool.submit(
                            _one_route, base_url, festival_id, destination, mock_scenario, timeout_s, poll_s
                        ))
                        if pacing == "sustained":
                            time.sleep(0.1)
                    rows = [future.result() for future in as_completed(futures)]
                summary = _summarize(f"{pattern}_{pacing}_{mock_scenario}", destinations, rows, time.monotonic() - started)
                summary.update({
                    "sequence": len(scenarios) + 1,
                    "destination_pattern": pattern,
                    "pacing": pacing,
                    "pacing_interval_s": 0.1 if pacing == "sustained" else 0,
                    "mock_scenario": mock_scenario,
                })
                scenarios.append(summary)
    return {
        "run_id": "w96_" + uuid4().hex[:16],
        "started_at": started_at,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "mode": "local_mock_only",
        "cache_state": "unverified",
        "internal_dedup_rate": "not_measured",
        "provider_latency": "not_measured",
        "limitations": "모의 응답의 API 시간만 측정했습니다. cold/warm 캐시·실제 공급원·내부 큐 효과는 검증 전입니다.",
        "festival_id": festival_id,
        "settings": {
            "requests_per_scenario": count, "concurrency": concurrency,
            "poll_s": poll_s, "timeout_s": timeout_s,
            "scenario_order": [item["scenario"] for item in scenarios],
        },
        "scenarios": scenarios,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="W96 로컬 모의 귀가 부하 예비 계측")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--festival-id", default="fst_000001")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--poll-s", type=float, default=2.0)
    parser.add_argument("--timeout-s", type=float, default=5.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_probe(args.base_url, args.festival_id, args.count, args.concurrency, args.poll_s, args.timeout_s)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"모의 부하 시험 결과 저장: {args.output} ({result['run_id']})")


if __name__ == "__main__":
    main()
