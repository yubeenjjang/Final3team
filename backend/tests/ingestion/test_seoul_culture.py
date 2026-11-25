import json
import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import httpx2
import pytest

from api.ingestion.festivals.normalize import KST
from api.ingestion.festivals.store import JobResult
from api.ingestion.seoul_culture import client as seoul_culture, collect
from api.ingestion.seoul_culture.normalize import normalize_event, normalized_title
from api.jobs import locks, scheduler

NOW = datetime(2026, 11, 25, 6, tzinfo=KST)
SERVICE = "culturalEventInfo"
KEY = "synthetic/src2+key"


@pytest.fixture
def source_rows():
    path = Path(__file__).resolve().parents[3] / "Docs/Step 2/evidence/responses/2026-11-19_seoul-culture.json"
    return json.loads(path.read_text(encoding="utf-8"))[SERVICE]["row"]


def source_body(rows, *, total=None):
    return {SERVICE: {
        "RESULT": {"CODE": "INFO-000"}, "list_total_count": len(rows) if total is None else total,
        "row": rows,
    }}


def festival_row(row, *, item_id="900001", **fields):
    return {
        **row, "CODENAME": "축제-문화/예술", "TITLE": "2027 서울 빛 축제",
        "HMPG_ADDR": row["HMPG_ADDR"].replace("160198", item_id),
        **fields,
    }


def test_real_fixture_filters_all_nonfestivals_and_records_inverted_dates(source_rows):
    results = [normalize_event(row, NOW.date()) for row in source_rows]
    assert [event for event, _, _ in results] == [None] * 5
    assert [(item_id, reason) for _, item_id, reason in results if reason] == [("160235", "DATE_INVALID")]


def test_normalizes_festival_fields_from_fixture_shape(source_rows):
    row = festival_row(source_rows[0], USE_FEE="", IS_FREE="무료", TITLE=" ２０２７ 서울 빛-축제 ")
    event, item_id, reason = normalize_event(row, NOW.date())
    assert reason is None
    assert item_id == event.source_item_id == "900001"
    assert normalized_title(event.title) == "2027서울빛축제"
    assert event.start_date.isoformat() == "2027-02-12"
    assert event.end_date.isoformat() == "2027-02-28"
    assert (event.latitude, event.longitude) == (37.485605, 127.028079)
    assert event.official_url == row["ORG_LINK"]
    assert event.source_image_url == row["MAIN_IMG"]
    assert event.admission_fee_text == "무료"
    assert normalize_event({**row, "ORG_LINK": "javascript:alert(1)", "LAT": "NaN"}, NOW.date())[0].official_url is None
    assert normalize_event({**row, "STRTDATE": "2027-02-30"}, NOW.date())[2] == "DATE_INVALID"
    assert normalize_event({**row, "HMPG_ADDR": "https://example.invalid/?cultcode=9"}, NOW.date())[2] == "REQUIRED_FIELD"


@pytest.mark.parametrize("category", ["콘서트", "교육/체험", "전시/미술", "클래식", "축제/공연", "", None])
def test_unknown_and_nonfestival_classes_are_excluded_even_with_festival_title(source_rows, category):
    row = festival_row(source_rows[0], CODENAME=category, THEMECODE="축제")
    assert normalize_event(row, NOW.date()) == (None, "900001", None)


def test_fetch_paginates_and_redacts_keys(monkeypatch, caplog, source_rows):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    monkeypatch.setattr(seoul_culture, "PAGE_SIZE", 3)
    caplog.set_level(logging.INFO, logger="httpx2")
    rows = [dict(source_rows[0], PLAYER=KEY), *source_rows[1:]]
    ranges = []

    def respond(request):
        assert request.url.host == "openapi.seoul.go.kr"
        assert request.url.raw_path.startswith(b"/synthetic%2Fsrc2%2Bkey/json/culturalEventInfo/")
        start, end = map(int, request.url.raw_path.rsplit(b"/", 2)[-2:])
        ranges.append((start, end))
        return httpx2.Response(200, json=source_body(rows[start - 1:end], total=len(rows)))

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as http:
        assert seoul_culture.fetch_events(http) == [{**rows[0], "PLAYER": "***"}, *rows[1:]]
    assert ranges == [(1, 3), (4, 5)]
    assert KEY not in caplog.text
    assert "synthetic%2Fsrc2%2Bkey" not in caplog.text


@pytest.mark.parametrize(("body", "code"), [
    ({"RESULT": {"CODE": "ERROR-310", "MESSAGE": KEY}}, "RESULT_ERROR"),
    ({SERVICE: {"RESULT": {"CODE": "INFO-000"}, "list_total_count": 30, "row": []}}, "INCOMPLETE_LISTING"),
    ([], "INVALID_RESPONSE"),
])
def test_fetch_rejects_provider_errors_and_incomplete_lists(monkeypatch, body, code):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=body))) as http:
        with pytest.raises(seoul_culture.SeoulCultureError, match=f"^{code}$"):
            seoul_culture.fetch_events(http)


def test_collect_records_fixture_rejects(monkeypatch, source_rows):
    store = Mock()
    store.finish_job.return_value = JobResult("fixture", "partial", 5, 0, 0, 5)
    monkeypatch.setattr(collect, "SeoulCultureStore", Mock(return_value=store))
    monkeypatch.setattr(collect, "fetch_events", Mock(return_value=source_rows))
    result = collect.collect_to_db(NOW, locked_engine=Mock())
    assert result.rejected == 5
    store.finish_job.assert_called_once_with(store.start_job.return_value, [], 5, [
        {"content_id": "160235", "stage": SERVICE, "code": "DATE_INVALID"},
    ])


def test_collect_records_safe_failure_without_key(monkeypatch):
    store = Mock()
    monkeypatch.setattr(collect, "SeoulCultureStore", Mock(return_value=store))
    monkeypatch.delenv("SEOUL_OPEN_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="목록 수집에 실패"):
        collect.collect_to_db(NOW, locked_engine=Mock())
    store.finish_job.assert_called_once_with(store.start_job.return_value, [], 0, [
        {"content_id": None, "stage": SERVICE, "code": "NO_KEY"},
    ], failed=True)


def test_collect_rejects_conflicting_items_with_same_source_id(monkeypatch, source_rows):
    store = Mock()
    row = festival_row(source_rows[0])
    monkeypatch.setattr(collect, "SeoulCultureStore", Mock(return_value=store))
    monkeypatch.setattr(collect, "fetch_events", Mock(return_value=[row, {**row, "TITLE": "다른 축제"}]))
    collect.collect_to_db(NOW, locked_engine=Mock())
    store.finish_job.assert_called_once_with(store.start_job.return_value, [], 2, [
        {"content_id": "900001", "stage": SERVICE, "code": "CONFLICTING_SOURCE_ID"},
    ])


def test_scheduler_is_opt_in_at_six_and_runs_after_tourapi(monkeypatch):
    monkeypatch.delenv("SEOUL_CULTURE_ENABLED", raising=False)
    run = Mock(return_value={})
    monkeypatch.setattr(scheduler, "_run_once", run)
    assert scheduler.run_due(NOW) == 0
    assert all(call.args[0].name != "collect_seoul_culture" for call in run.call_args_list)

    monkeypatch.setenv("SEOUL_CULTURE_ENABLED", "true")
    run.reset_mock()
    assert scheduler.run_due(NOW.replace(hour=5, minute=59)) == 0
    assert all(call.args[0].name != "collect_seoul_culture" for call in run.call_args_list)
    run.reset_mock()
    assert scheduler.run_due(NOW) == 0
    tourapi, seoul = [call.args[0] for call in run.call_args_list[-2:]]
    assert (tourapi.name, seoul.name) == ("collect_festivals", "collect_seoul_culture")
    assert seoul.lock is tourapi.lock is locks.FESTIVALS
    assert run.call_args.args[1] == NOW

    db = Mock()
    collect_db = Mock(return_value=JobResult("fixture", "partial", 5, 0, 0, 5))
    monkeypatch.setattr(collect, "collect_to_db", collect_db)
    assert seoul.run(db, NOW) == {"scanned": 5, "inserted": 0, "updated": 0, "rejected": 5}
    collect_db.assert_called_once_with(NOW, locked_engine=db.get_bind.return_value)
