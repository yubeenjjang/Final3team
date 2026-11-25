#!/usr/bin/env python3
"""실제·모의 API를 호출하고 허용된 응답 필드만 JSON으로 출력한다."""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4


FESTIVALS = "/api/v1/festivals"
SEARCH = FESTIVALS + "?status=ongoing,upcoming&region=SEOUL"
RETURN_ROUTE = "/api/v1/routes/return"
DESTINATION = "서울역"
PENDING = {"queued", "processing"}
FINAL = {"ready", "unavailable", "timed_out", "rejected"}
MOCK_FAILURES = {
    "async_unavailable": ("unavailable", "ROUTE_UPSTREAM_ERROR", True),
    "async_timeout": ("timed_out", "ROUTE_TIMEOUT", True),
    "async_secondary_sync_only": ("unavailable", "ROUTE_SECONDARY_SYNC_ONLY", True),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


HTTP = build_opener(ProxyHandler({}), NoRedirect())


def base_url(value):
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
    ):
        raise argparse.ArgumentTypeError("기본 주소만 지정하세요. 예시 http://127.0.0.1:18000")
    return value.rstrip("/")


def request(base, path, steps, api, *, body=None, headers=None):
    method = "POST" if body is not None else "GET"
    request_headers = {"Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(
        base + path,
        method=method,
        headers=request_headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    row = {"api": api, "method": method, "path": path}
    steps.append(row)
    started = time.perf_counter()
    try:
        try:
            response = HTTP.open(req, timeout=15)
        except HTTPError as exc:
            response = exc
        with response:
            row["http"] = response.code
            request_id = response.headers.get("X-Request-ID")
            mock = response.headers.get("X-Mock")
            row["response_headers"] = {
                "X-Request-ID_present": request_id is not None,
                "X-Request-ID": request_id if re.fullmatch(r"req_[A-Za-z0-9]{26}", request_id or "") else None,
                "X-Mock_present": mock is not None,
                "X-Mock": mock.lower() if mock and mock.lower() in {"true", "false"} else None,
            }
            result = json.load(response)
    except (OSError, URLError, ValueError):
        result = None
    row["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if not isinstance(result, dict):
        raise RuntimeError("HTTP 응답 본문을 JSON 객체로 읽지 못했습니다.")
    return row, result


def record_mode(row, body):
    mock = body.get("is_mock")
    if type(mock) is bool:
        row["is_mock"] = mock


def matching_mode(row, mock):
    headers = row["response_headers"]
    return (
        row.get("is_mock") is mock
        and headers["X-Mock_present"] is mock
        and (not mock or headers["X-Mock"] == "true")
    )


def festival_summary(body):
    keys = ("festival_id", "name", "region_code", "venue_name", "event_status", "source")
    return {key: body[key] for key in keys if key in body}


def route_summary(row, body):
    record_mode(row, body)
    status = body.get("route_status")
    if status in PENDING | FINAL:
        row["route_status"] = status
    route_id = body.get("route_request_id")
    if isinstance(route_id, str) and re.fullmatch(r"rr_[A-Za-z0-9]{6,26}", route_id):
        row["route_request_id"] = route_id
    if body.get("status_url") == f"{RETURN_ROUTE}/{row.get('route_request_id')}" and "route_request_id" in row:
        row["status_url"] = body["status_url"]
    if "route_access_token" in body:
        row["route_access_token"] = "***"
    for key, value_type in (("completed_valid_route", bool), ("retry_after_s", int)):
        if type(body.get(key)) is value_type:
            row[key] = body[key]
    for key, values in (("provider", ("tmap", "kakao", "mock")), ("provider_tier", ("primary", "secondary", "mock"))):
        if body.get(key) in values:
            row[key] = body[key]
    candidates = body.get("route_candidates")
    row["route_count"] = len(candidates) if isinstance(candidates, list) else 0
    if isinstance(candidates, list):
        row["duration_minutes"] = [
            candidate.get("duration_min") if type(candidate.get("duration_min")) is int else None
            for candidate in candidates
        ]
    error = body.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        row["error"] = {
            "code": code if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z_0-9]{2,63}", code) else None,
            "retryable": error.get("retryable") if type(error.get("retryable")) is bool else None,
        }


def find_festival(base, steps, *, mock):
    search, body = request(base, SEARCH, steps, "A02")
    record_mode(search, body)
    if search["http"] != 200 or not matching_mode(search, mock):
        raise RuntimeError("A02에서 예상한 축제 모드를 확인하지 못했습니다.")
    search["total"] = body["total"]
    usable = [
        item for item in body["items"]
        if re.fullmatch(r"fst_[A-Za-z0-9]{6,26}", item["festival_id"])
        and item["event_status"] in {"ongoing", "upcoming"}
        and item["lat"] is not None and item["lng"] is not None
    ]
    if not usable:
        raise RuntimeError("A02 서울 결과에 출발지로 쓸 축제가 없습니다.")
    chosen = min(usable, key=lambda item: (item["name"] != "DDP 건축투어", item["event_status"] != "ongoing"))
    search["selected_festival"] = festival_summary(chosen)
    festival_id = chosen["festival_id"]
    detail, body = request(base, f"{FESTIVALS}/{festival_id}", steps, "A03")
    record_mode(detail, body)
    if detail["http"] != 200 or body.get("festival_id") != festival_id or not matching_mode(detail, mock):
        raise RuntimeError("A03에서 같은 축제 ID와 예상한 축제 모드를 확인하지 못했습니다.")
    detail["festival"] = festival_summary(body)
    return festival_id


def run_route(base, festival_id, steps, *, scenario=None):
    mock = scenario is not None
    headers = {"X-Mock-Scenario": scenario} if mock else {}
    row, body = request(base, RETURN_ROUTE, steps, "A04", headers=headers, body={
        "request_id": str(uuid4()),
        "festival_id": festival_id,
        "origin": {"type": "festival"},
        "destination": {"query": DESTINATION},
    })
    row["festival_id"] = festival_id
    route_summary(row, body)
    if row["http"] not in {200, 202} or not matching_mode(row, mock):
        raise RuntimeError("A04에서 예상한 HTTP 코드와 경로 모드를 확인하지 못했습니다.")
    if row["http"] == 200:
        return row

    path = row.get("status_url")
    token = body.get("route_access_token")
    if not path or not isinstance(token, str) or not token:
        raise RuntimeError("A04 202 응답에 유효한 조회 주소와 조회 토큰이 없습니다.")
    route_id = row["route_request_id"]
    for _ in range(5):
        time.sleep(2)
        row, body = request(base, path, steps, "A05", headers={"X-Route-Access-Token": token})
        row["request_headers"] = {"X-Route-Access-Token": "***"}
        route_summary(row, body)
        if row["http"] != 200 or not matching_mode(row, mock) or row.get("route_request_id") != route_id:
            raise RuntimeError("A05에서 예상한 HTTP 코드와 경로 모드 또는 요청 ID를 확인하지 못했습니다.")
        if row.get("route_status") in FINAL:
            return row
        if row.get("route_status") not in PENDING:
            raise RuntimeError("A05가 예상한 상태값을 반환하지 않았습니다.")
    raise RuntimeError("A05를 다섯 번 조회하는 동안 종료 상태가 나오지 않았습니다.")


def real_flow(base, record):
    steps = record["steps"]
    festival_id = find_festival(base, steps, mock=False)
    final = run_route(base, festival_id, steps)
    if final.get("route_status") != "ready" or final.get("completed_valid_route") is not True or final["route_count"] == 0:
        raise RuntimeError("실제 경로가 ready 상태와 유효한 후보를 반환하지 않았습니다.")


def mock_flow(base, record):
    festival_id = find_festival(base, record["steps"], mock=True)
    # 토큰 없는 GET으로 경로 라우터의 모의 모드를 확인한 뒤에만 POST한다.
    probe, _ = request(base, RETURN_ROUTE + "/rr_modeprobe", record["steps"], "모의 경로 사전 확인")
    if probe["http"] != 401 or probe["response_headers"]["X-Mock"] != "true":
        raise RuntimeError("모의 경로 모드를 확인하지 못해 시나리오 요청을 건너뛰었습니다.")
    for scenario, expected in MOCK_FAILURES.items():
        steps = []
        result = {"scenario": scenario, "steps": steps}
        record["scenarios"].append(result)
        try:
            final = run_route(base, festival_id, steps, scenario=scenario)
            state = [(step["http"], step.get("route_status")) for step in steps]
            error = final.get("error", {})
            observed = (final.get("route_status"), error.get("code"), error.get("retryable"))
            if state != [(202, "queued"), (200, "processing"), (200, expected[0])] or observed != expected:
                raise RuntimeError("모의 상태 전이 또는 오류 코드와 재시도 가능 값이 예상과 다릅니다.")
        except RuntimeError as exc:
            result["problem"] = str(exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("real_url", type=base_url)
    parser.add_argument("mock_url", type=base_url)
    args = parser.parse_args()
    if args.real_url == args.mock_url:
        parser.error("실제 서버와 모의 서버에 서로 다른 기본 주소를 지정하세요.")

    report = {
        "started_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
        "destination": DESTINATION,
        "real": {"steps": []},
        "mock": {"steps": [], "scenarios": []},
    }
    for flow, url, record in (
        (real_flow, args.real_url, report["real"]),
        (mock_flow, args.mock_url, report["mock"]),
    ):
        try:
            flow(url, record)
        except RuntimeError as exc:
            record["problem"] = str(exc)
        except (KeyError, TypeError, ValueError):
            record["problem"] = "예상한 API 응답 구조를 확인하지 못했습니다."

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(any("problem" in record for record in [report["real"], report["mock"], *report["mock"]["scenarios"]]))


if __name__ == "__main__":
    sys.exit(main())
