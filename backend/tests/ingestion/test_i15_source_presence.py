from contextlib import nullcontext
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import httpx2
import pytest
from sqlalchemy import Engine, text

from api.ingestion.festivals import collect
from api.ingestion.festivals.store import ListingScope

from .test_i8_collect import TEST_KEY, listing, output_files, run_collector

ITEM_ID = "3379778"


@pytest.fixture(autouse=True)
def set_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", TEST_KEY)


def list_response(page: int, *, total: int, present: bool = True, title: str | None = None) -> httpx2.Response:
    payload = listing()
    body = payload["response"]["body"]
    item = body["items"]["item"][0]
    if title is not None:
        item.update(title=title, modifiedtime="20261123090000")
    body.update(pageNo=page, totalCount=total, items={"item": [item] if present else []})
    return httpx2.Response(200, json=payload)


@pytest.mark.parametrize("scenario", ["complete", "failed_page", "quota", "duplicate", "limit"])
def test_I15_only_complete_listing_is_forwarded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scenario: str,
) -> None:
    store = Mock()
    store.load.return_value = {}
    store.finish_job.return_value = None
    engine = Mock()
    lock = Mock()
    lock.scalar.return_value = True
    lock.get_bind.return_value = engine
    monkeypatch.setattr(collect, "service_db_session", lambda: nullcontext(lock))
    monkeypatch.setattr(collect, "FestivalStore", lambda engine: store)
    if scenario == "quota":
        monkeypatch.setattr("api.providers.tourapi.LIST_CALL_LIMIT", 1)
    pages = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        page = int(request.url.params["pageNo"])
        pages.append(page)
        if scenario == "failed_page" and page == 2:
            return httpx2.Response(503)
        return list_response(page, total=1 if scenario in {"complete", "limit"} else 2)

    args = ("--limit", "1") if scenario == "limit" else ()
    failed = scenario in {"failed_page", "quota", "duplicate"}
    assert run_collector(tmp_path, handler, "--db", "--no-detail", *args) == int(failed)
    kwargs = store.finish_job.call_args.kwargs
    assert kwargs["failed"] is failed
    expected_scope = ListingScope(date(2026, 1, 1), None) if scenario == "complete" else None
    assert kwargs["scope"] == expected_scope
    assert pages == {
        "complete": [1], "failed_page": [1, 2, 2], "quota": [1], "duplicate": [1, 2], "limit": [1],
    }[scenario]


def festival_state(engine: Engine) -> tuple[str, bool, str, str]:
    with engine.connect() as connection:
        return tuple(connection.execute(text(
            "SELECT review_status, published_at IS NOT NULL, event_status, title"
            " FROM festivals JOIN festival_sources USING (festival_id) WHERE source_item_id = :item"
        ), {"item": ITEM_ID}).one())


@pytest.mark.db
def test_I16_I17_same_scope_missing_and_reappearance_keep_review(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    original = lambda request: list_response(1, total=1)
    empty = lambda request: list_response(1, total=0, present=False)
    assert run_collector(tmp_path, original, "--db", "--no-detail") == 0
    initial = festival_state(db_engine)
    assert initial[:2] == ("approved", True)

    # 시작 날짜가 축제를 포함해도 종료 조건이 달라진 첫 수집은 비교하지 않는다.
    assert run_collector(tmp_path, empty, "--db", "--no-detail", "--until", "2026-12-31") == 0
    assert festival_state(db_engine) == initial

    assert run_collector(tmp_path, empty, "--db", "--no-detail") == 0
    _, report = output_files(tmp_path)
    missing_job = report["db"]["job_id"]
    assert festival_state(db_engine) == ("pending", False, *initial[2:])
    assert run_collector(tmp_path, empty, "--db", "--no-detail") == 0

    assert run_collector(tmp_path, original, "--db", "--no-detail") == 0
    _, report = output_files(tmp_path)
    return_job = report["db"]["job_id"]
    assert festival_state(db_engine) == ("pending", False, *initial[2:])
    updated = lambda request: list_response(1, total=1, title="재등장 후 수정한 축제")
    assert run_collector(tmp_path, updated, "--db", "--no-detail") == 0
    assert festival_state(db_engine) == ("pending", False, initial[2], "재등장 후 수정한 축제")

    with db_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT reason, approval_status FROM festival_review_queue"
        )).one() == ("missing_from_source", "pending")
        assert connection.execute(text(
            "SELECT error #> '{listing,ids}' FROM ingestion_jobs WHERE job_id = :job"
        ), {"job": missing_job}).scalar_one() == []
        history = dict(connection.execute(text(
            "SELECT field, after_value FROM festival_change_history"
            " WHERE field IN ('review_status', 'published_at')"
        )).all())
        assert history == {"review_status": "pending", "published_at": None}
        assert connection.execute(text(
            "SELECT after_value FROM festival_change_history"
            " WHERE field = 'source_presence' ORDER BY change_id"
        )).scalars().all() == [
            {"job_id": missing_job, "reason": "missing_from_source"},
            {"job_id": return_job, "reason": "reappeared_in_source"},
        ]


@pytest.mark.db
def test_I15_page_failure_leaves_public_festival_and_no_history(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    assert run_collector(tmp_path, lambda request: list_response(1, total=1), "--db", "--no-detail") == 0

    def interrupted(request: httpx2.Request) -> httpx2.Response:
        if request.url.params["pageNo"] == "1":
            return httpx2.Response(200, json={"response": {
                "header": {"resultCode": "0000"},
                "body": {"totalCount": 2, "items": {"item": {"contentid": "other"}}},
            }})
        return httpx2.Response(429)

    assert run_collector(tmp_path, interrupted, "--db", "--no-detail") == 1
    assert festival_state(db_engine)[:2] == ("approved", True)
    with db_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM festival_change_history")).scalar_one() == 0


@pytest.mark.db
def test_I18_legacy_public_row_missing_from_first_baseline_is_held_for_classification(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    original = lambda request: httpx2.Response(200, json=listing())
    empty = lambda request: list_response(1, total=0, present=False)
    assert run_collector(tmp_path, original, "--db", "--no-detail", "--limit", "2") == 0
    with db_engine.begin() as connection:
        connection.execute(text("""
            UPDATE festivals SET source_class_level2 = NULL, source_class_code = NULL
            FROM festival_sources
            WHERE festivals.festival_id = festival_sources.festival_id AND source_item_id = :item
        """), {"item": ITEM_ID})

    assert run_collector(tmp_path, empty, "--db", "--no-detail") == 0
    _, report = output_files(tmp_path)
    assert festival_state(db_engine)[:2] == ("pending", False)
    assert run_collector(tmp_path, empty, "--db", "--no-detail") == 0
    with db_engine.connect() as connection:
        assert connection.execute(text("""
            SELECT source_item_id FROM festival_sources JOIN festivals USING (festival_id)
            WHERE review_status = 'approved' AND published_at IS NOT NULL
        """)).scalar_one() == "2536122"
        assert connection.execute(text("""
            SELECT field, after_value FROM festival_change_history
            WHERE field IN ('source_classification', 'source_presence')
        """)).one() == (
            "source_classification", {"reason": "class_unverified", "job_id": report["db"]["job_id"]},
        )
