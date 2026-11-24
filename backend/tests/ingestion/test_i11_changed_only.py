from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
import pytest
from sqlalchemy import Engine, text

from api.ingestion.festivals import collect
from api.ingestion.festivals.normalize import KST, normalize_festival
from api.ingestion.festivals.store import DETAIL_FIELDS, ErrorEntry, StoredFestival
from api.providers.tourapi import TourApiClient

from .test_i8_collect import TEST_KEY, fixture_response, listing, output_files, run_collector

TODAY = date(2026, 11, 23)
VERSION = datetime(2026, 10, 6, tzinfo=KST)


@pytest.fixture(autouse=True)
def set_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", TEST_KEY)


def mock_responses(payload: dict[str, Any]) -> Callable[[httpx2.Request], httpx2.Response]:
    def handler(request: httpx2.Request) -> httpx2.Response:
        endpoint = request.url.path.rsplit("/", 1)[-1]
        if endpoint == "searchFestival2":
            return httpx2.Response(200, json=payload)
        content_id = request.url.params["contentId"]
        prefix = {"detailIntro2": "intro", "detailCommon2": "common"}[endpoint]
        return fixture_response(f"{prefix}_{content_id}.json")
    return handler


@pytest.mark.parametrize(
    ("version", "previous", "fetch"),
    [
        (None, None, True),
        (VERSION, StoredFestival(None, "cached", {}), True),
        (VERSION + timedelta(seconds=1), StoredFestival(VERSION, "cached", {}), True),
        (VERSION, StoredFestival(VERSION, "cached", {}), False),
        (VERSION - timedelta(seconds=1), StoredFestival(VERSION, "cached", {}), False),
        (None, StoredFestival(VERSION, "cached", {}), False),
        (None, StoredFestival(None, "cached", {}), False),
    ],
)
def test_I11_refresh_requires_new_item_or_newer_version(
    version: datetime | None, previous: StoredFestival | None, fetch: bool,
) -> None:
    assert collect.should_fetch_details(version, previous) is fetch


def test_I11_same_version_keeps_details_and_checksum() -> None:
    payload = listing()
    items = payload["response"]["body"]["items"]["item"][:2]
    previous = {}
    for item in items:
        record = normalize_festival(item, today=TODAY, details_requested=False)
        details = dict.fromkeys(DETAIL_FIELDS, "기존 상세")
        previous[record.source_item_id] = StoredFestival(record.source_updated_at, "cached", details)
    items[1]["modifiedtime"] = "20261101090000"
    errors: list[ErrorEntry] = []
    with httpx2.Client(transport=httpx2.MockTransport(mock_responses(payload))) as http_client:
        with TourApiClient(http_client) as client:
            unchanged, changed = collect._normalize_items(
                client, items, TODAY, False, Counter(), errors, previous,
            )
            assert client.calls == {"detailCommon2": 1, "detailIntro2": 1}
    assert not errors
    assert unchanged.raw_checksum == "cached"
    assert all(getattr(unchanged, name) == "기존 상세" for name in DETAIL_FIELDS)
    assert changed.raw_checksum != "cached"
    assert changed.source_updated_at == datetime(2026, 11, 1, 9, tzinfo=KST)


def test_I11_detail_error_keeps_saved_details_and_can_retry() -> None:
    payload = listing()
    item = payload["response"]["body"]["items"]["item"][0]
    source_item_id = item["contentid"]
    previous = StoredFestival(VERSION, "cached", dict.fromkeys(DETAIL_FIELDS, "기존 상세"))

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/detailCommon2"):
            return httpx2.Response(503)
        return fixture_response(f"intro_{source_item_id}.json")

    errors: list[ErrorEntry] = []
    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http_client:
        with TourApiClient(http_client) as client:
            [record] = collect._normalize_items(
                client, [item], TODAY, False, Counter(), errors, {source_item_id: previous},
            )
    assert [error["stage"] for error in errors] == ["detailCommon2"]
    assert record.summary == record.venue_name == "기존 상세"
    assert record.source_updated_at == VERSION
    listing_record = normalize_festival(item, today=TODAY, details_requested=False)
    assert collect.should_fetch_details(listing_record.source_updated_at, previous)


@pytest.mark.db
def test_I19_reclassifies_legacy_rows_with_cached_details_and_is_idempotent(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(collect, "create_ingestion_engine", lambda: db_engine)
    payload = listing()
    body = payload["response"]["body"]
    items = body["items"]["item"]
    handler = mock_responses(payload)
    assert run_collector(tmp_path / "initial", handler, "--db") == 0
    with db_engine.begin() as connection:
        connection.execute(text("""
            UPDATE festivals SET source_class_level1 = NULL, source_class_level2 = NULL, source_class_code = NULL
        """))
        connection.execute(text("""
            UPDATE festivals SET review_status = 'hidden'
            WHERE festival_id = (SELECT festival_id FROM festival_sources WHERE source_item_id = '3486674')
        """))
        before = connection.execute(text("""
            SELECT source_item_id, raw_checksum, summary, published_at
            FROM festival_sources JOIN festivals USING (festival_id)
        """)).mappings().all()
    previous = {row["source_item_id"]: row for row in before}

    items[0].update(lclsSystm2="EV02", lclsSystm3="EV020100")
    items[1].update(lclsSystm2="EV03", lclsSystm3="EV030100")
    items[2].update(lclsSystm1="", lclsSystm2="", lclsSystm3="")
    items[3].update(lclsSystm2="EV02", lclsSystm3="EV020100")
    items.append(items[1] | {"contentid": "1234567"})
    body["totalCount"] = len(items)

    assert run_collector(tmp_path / "reclassified", handler, "--db", "--no-detail") == 0
    _, report = output_files(tmp_path / "reclassified")
    assert report["calls"] == {"searchFestival2": 1}
    assert report["issues"]["not_festival_class"] == 5
    assert (report["db"]["inserted"], report["db"]["updated"]) == (1, 5)
    job_id = report["db"]["job_id"]

    assert run_collector(tmp_path / "repeated", handler, "--db", "--no-detail") == 0
    _, repeated = output_files(tmp_path / "repeated")
    assert (repeated["db"]["inserted"], repeated["db"]["updated"]) == (0, 0)
    with db_engine.connect() as connection:
        rows = connection.execute(text("""
            SELECT source_item_id, raw_checksum, summary, category, source_class_level1,
                   source_class_level2, source_class_code, review_status, published_at
            FROM festival_sources JOIN festivals USING (festival_id) ORDER BY source_item_id
        """)).all()
        assert {row[0]: row[3:] for row in rows} == {
            "1234567": ("event", "EV", "EV03", "EV030100", "pending", None),
            "2536122": ("event", "EV", "EV03", "EV030100", "pending", None),
            "2865122": ("festival", "EV", "EV01", "EV010200", "pending", None),
            "292950": ("unknown", None, None, None, "pending", None),
            "3379778": ("performance", "EV", "EV02", "EV020100", "pending", None),
            "3486674": ("performance", "EV", "EV02", "EV020100", "hidden", previous["3486674"]["published_at"]),
        }
        for source_id, checksum, summary, *_ in rows:
            if source_id in previous:
                assert (checksum, summary) == (previous[source_id]["raw_checksum"], previous[source_id]["summary"])
        reasons = connection.execute(text("""
            SELECT source_item_id, after_value, actor FROM festival_change_history
            JOIN festival_sources USING (festival_id)
            WHERE field = 'source_classification' ORDER BY source_item_id
        """)).all()
        assert reasons == [
            (source_id, {"reason": "not_festival_class", "job_id": job_id}, "ingestion")
            for source_id in ("2536122", "292950", "3379778")
        ]
        assert connection.execute(text("""
            SELECT field, count(*) FROM festival_change_history
            WHERE field IN ('published_at', 'review_status') GROUP BY field ORDER BY field
        """)).all() == [("published_at", 3), ("review_status", 3)]

    items[0].update(lclsSystm2="EV01", lclsSystm3="EV010600")
    assert run_collector(tmp_path / "restored", handler, "--db", "--no-detail") == 0
    with db_engine.connect() as connection:
        assert connection.execute(text("""
            SELECT category, review_status, published_at IS NOT NULL
            FROM festival_sources JOIN festivals USING (festival_id) WHERE source_item_id = '3379778'
        """)).one() == ("festival", "approved", True)


@pytest.mark.db
def test_I11_collect_db_refetches_only_changed_item(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(collect, "create_ingestion_engine", lambda: db_engine)
    payload = listing()
    items = payload["response"]["body"]["items"]["item"]
    handler = mock_responses(payload)
    first_out = tmp_path / "first"
    assert run_collector(first_out, handler, "--db", "--limit", "2") == 0
    first, first_report = output_files(first_out)
    assert first_report["db"]["inserted"] == 2

    items[1].update(modifiedtime="20261101090000", title="수정한 축제")
    second_out = tmp_path / "second"
    assert run_collector(second_out, handler, "--db", "--limit", "2") == 0
    second, second_report = output_files(second_out)
    assert second_report["calls"] == {"searchFestival2": 1, "detailCommon2": 1, "detailIntro2": 1}
    assert (second_report["db"]["inserted"], second_report["db"]["updated"]) == (0, 1)
    assert second[0] == first[0]
    assert second[1]["title"] == "수정한 축제"

    third_out = tmp_path / "third"
    assert run_collector(third_out, handler, "--db", "--limit", "2") == 0
    _, third_report = output_files(third_out)
    assert third_report["calls"] == {"searchFestival2": 1}
    assert (third_report["db"]["inserted"], third_report["db"]["updated"]) == (0, 0)


@pytest.mark.db
def test_I10_collect_list_error_records_failed_job(
    db_engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(collect, "create_ingestion_engine", lambda: db_engine)

    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.url.path.endswith("/searchFestival2")
        return fixture_response("error_key.txt")

    assert run_collector(tmp_path, handler, "--db") == 1
    records, report = output_files(tmp_path)
    assert not records
    assert report["db"]["status"] == "failed"
    with db_engine.connect() as connection:
        status, ended_at, scanned, error = connection.execute(text(
            "SELECT status, ended_at, scanned, error FROM ingestion_jobs"
        )).one()
    assert (status, scanned, error) == ("failed", 0, report["errors"])
    assert ended_at is not None
