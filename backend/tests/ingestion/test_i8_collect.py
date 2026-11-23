import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
import pytest

from api.ingestion.festivals.collect import main

FIXTURES = Path(__file__).parent / "fixtures"
TEST_KEY = "TEST_KEY_DO_NOT_USE"


@pytest.fixture(autouse=True)
def set_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", TEST_KEY)


def listing() -> dict[str, Any]:
    return json.loads((FIXTURES / "search_page1.json").read_text(encoding="utf-8"))


def fixture_response(name: str) -> httpx2.Response:
    return httpx2.Response(200, content=(FIXTURES / name).read_bytes())


def run_collector(
    out: Path, handler: Callable[[httpx2.Request], httpx2.Response], *args: str
) -> int:
    with httpx2.Client(transport=httpx2.MockTransport(handler)) as client:
        return main(["--since", "2026-01-01", "--out", str(out), *args], http_client=client)


def output_files(out: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records_text = (out / "festivals.jsonl").read_text(encoding="utf-8")
    report_text = (out / "report.json").read_text(encoding="utf-8")
    assert TEST_KEY not in records_text
    assert TEST_KEY not in report_text
    return [json.loads(line) for line in records_text.splitlines()], json.loads(report_text)


@pytest.mark.parametrize("detail_fails", [False, True])
def test_I8_collect_fixture_and_report(tmp_path: Path, detail_fails: bool) -> None:
    seen = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        endpoint = request.url.path.rsplit("/", 1)[-1]
        seen.append(endpoint)
        assert request.url.params["serviceKey"] == TEST_KEY
        if endpoint == "searchFestival2":
            assert request.url.params["eventEndDate"] == "20261231"
            return fixture_response("search_page1.json")
        content_id = request.url.params["contentId"]
        if endpoint == "detailCommon2":
            if detail_fails and content_id == "3379778":
                return httpx2.Response(400, text=f"SERVICE_KEY={TEST_KEY}")
            return fixture_response(f"common_{content_id}.json")
        assert endpoint == "detailIntro2"
        return fixture_response(f"intro_{content_id}.json")

    out = tmp_path / "result"
    assert run_collector(out, handler, "--until", "2026-12-31") == 0
    records, report = output_files(out)
    items = listing()["response"]["body"]["items"]["item"]
    assert [record["source_item_id"] for record in records] == [item["contentid"] for item in items]
    assert records[0]["start_date"] == "2026-10-16"
    assert records[0]["source_updated_at"] == "2026-10-06T09:15:02+09:00"
    assert records[0]["venue_name"] == "가락몰 3층 하늘공원"
    assert records[0]["publishable"] is True
    assert seen == ["searchFestival2"] + ["detailCommon2", "detailIntro2"] * 5
    assert set(report) == {
        "started_at", "ended_at", "since", "until", "scanned", "publishable", "pending",
        "issues", "calls", "errors",
    }
    assert report["since"] == "2026-01-01"
    assert report["until"] == "2026-12-31"
    assert report["scanned"] == len(items) == 5
    assert (report["publishable"], report["pending"]) == (4, 1)
    assert report["calls"] == {"searchFestival2": 1, "detailCommon2": 5, "detailIntro2": 5}
    started_at = datetime.fromisoformat(report["started_at"])
    ended_at = datetime.fromisoformat(report["ended_at"])
    assert started_at.utcoffset() == ended_at.utcoffset() == timedelta(hours=9)
    assert started_at <= ended_at
    if detail_fails:
        assert records[0]["summary"] is None
        assert records[0]["issues"] == ["detail_missing"]
        assert report["issues"] == {"coords_out_of_range": 1, "detail_missing": 1}
        assert report["errors"] == [
            {"content_id": "3379778", "stage": "detailCommon2", "code": "KEY_ERROR"}
        ]
    else:
        assert records[0]["summary"]
        assert records[0]["issues"] == []
        assert report["issues"] == {"coords_out_of_range": 1}
        assert report["errors"] == []


def test_I8_no_detail_and_limit_still_fetch_all_pages(tmp_path: Path) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path.endswith("/searchFestival2")
        payload = listing()
        body = payload["response"]["body"]
        items = body["items"]["item"]
        body["items"]["item"] = items[:2] if request.url.params["pageNo"] == "1" else items[2:]
        return httpx2.Response(200, json=payload)

    assert run_collector(tmp_path, handler, "--no-detail", "--limit", "2") == 0
    records, report = output_files(tmp_path)
    assert [record["source_item_id"] for record in records] == ["3379778", "2536122"]
    assert all(record["summary"] is None and record["issues"] == [] for record in records)
    assert report["scanned"] == report["publishable"] == 2
    assert report["until"] is None
    assert report["calls"] == {"searchFestival2": 2}
    assert report["issues"] == {}


def test_I8_list_failure_exits_with_status_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path.endswith("/searchFestival2")
        return httpx2.Response(403, content=(FIXTURES / "error_key.txt").read_bytes())

    assert run_collector(tmp_path, handler) == 1
    records, report = output_files(tmp_path)
    assert records == []
    assert report["scanned"] == report["publishable"] == report["pending"] == 0
    assert report["calls"] == {"searchFestival2": 1}
    assert report["errors"] == [{"content_id": None, "stage": "searchFestival2", "code": "KEY_ERROR"}]
    stderr = capsys.readouterr().err
    assert "KEY_ERROR" in stderr
    assert TEST_KEY not in stderr


def test_I8_detail_quota_counts_retries_without_exceeding_900(tmp_path: Path) -> None:
    payload = listing()
    body = payload["response"]["body"]
    source = body["items"]["item"][0]
    body["totalCount"] = 902
    items = [source | {"contentid": str(i)} for i in range(1, 903)]
    common = (FIXTURES / "common_3379778.json").read_bytes()
    intro = (FIXTURES / "intro_3379778.json").read_bytes()
    first_common = True

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal first_common
        endpoint = request.url.path.rsplit("/", 1)[-1]
        if endpoint == "searchFestival2":
            begin = (int(request.url.params["pageNo"]) - 1) * 100
            body["items"]["item"] = items[begin : begin + 100]
            return httpx2.Response(200, json=payload)
        content_id = int(request.url.params["contentId"])
        assert content_id <= 899
        if endpoint == "detailCommon2":
            if content_id == 1 and first_common:
                first_common = False
                return httpx2.Response(503)
            if content_id == 899:
                return httpx2.Response(503)
            return httpx2.Response(200, content=common)
        assert endpoint == "detailIntro2"
        return httpx2.Response(200, content=intro)

    assert run_collector(tmp_path, handler) == 0
    records, report = output_files(tmp_path)
    assert len(records) == report["scanned"] == 902
    assert report["calls"] == {"searchFestival2": 10, "detailCommon2": 900, "detailIntro2": 899}
    assert report["issues"] == {"detail_missing": 1, "detail_skipped_quota": 3}
    assert report["errors"] == [
        {"content_id": "899", "stage": "detailCommon2", "code": "HTTP_ERROR"}
    ]
    assert records[897]["venue_name"]
    assert records[898]["issues"] == ["detail_missing"]
    assert all(record["venue_name"] is None and record["issues"] == [] for record in records[899:])
