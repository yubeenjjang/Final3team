from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Barrier

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.ingestion.festivals.normalize import normalize_festival
from api.ingestion.festivals.store import FestivalStore
from api.ingestion.seoul_culture import collect

from .test_i12_catalog_db import app_engine
from .test_seoul_culture import KEY, NOW, festival_row, source_body, source_rows

pytestmark = pytest.mark.db


def seed_tourapi(engine, *, title="2027 서울빛축제", item_id="1234567", **fields):
    start = NOW - timedelta(days=1)
    record = normalize_festival({
        "contentid": item_id, "title": title, "lDongRegnCd": "11",
        "lclsSystm2": "EV01", "eventstartdate": "20270201", "eventenddate": "20270212",
        "mapy": "37.486", "mapx": "127.028", "modifiedtime": "20261123100000",
        "firstimage": "https://example.invalid/tour-image", "firstimage2": "https://example.invalid/tour-thumbnail",
        "cpyrhtDivCd": "Type3", **fields,
    }, {"overview": "TourAPI 소개"}, today=NOW.date())
    store = FestivalStore(engine)
    assert store.finish_job(store.start_job(start), [record], []).inserted == 1
    with engine.connect() as db:
        festival_id = db.scalar(text(
            "SELECT festival_id FROM festival_sources WHERE source_id = 'tourapi' AND source_item_id = :item"
        ), {"item": item_id})
    return festival_id, record


def run_collection(engine, rows, *, now=NOW):
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=source_body(rows)))) as http:
        return collect.collect_to_db(now, locked_engine=engine, http_client=http)


def test_src2_merges_gaps_and_preserves_tourapi_updates(db_engine, monkeypatch, source_rows):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    festival_id, tour = seed_tourapi(db_engine)
    row = festival_row(source_rows[0], TITLE="２０２７ 서울 빛-축제")
    params = {"id": festival_id}

    result = run_collection(db_engine, [row, *source_rows])
    assert (result.status, result.scanned, result.inserted, result.updated, result.rejected) == ("partial", 6, 0, 1, 5)
    with db_engine.connect() as db:
        festival = db.execute(text("SELECT * FROM festivals WHERE festival_id = :id"), params).mappings().one()
        assert festival["title"] == tour.title
        assert festival["image_url"] == tour.image_url
        assert festival["thumbnail_url"] == tour.thumbnail_url
        assert festival["summary"] == tour.summary
        assert festival["official_url"] == row["ORG_LINK"]
        assert festival["admission_fee_text"] == row["USE_FEE"]
        assert festival["review_status"] == "approved" and festival["published_at"] is not None
        assert db.scalar(text("SELECT count(*) FROM festivals")) == 1
        assert db.scalar(text("SELECT count(*) FROM festival_review_queue")) == 0
        assert db.execute(text("""
            SELECT source_item_id, source_url, source_image_url, last_job_id FROM festival_sources
            WHERE festival_id = :id AND source_id = 'seoul_culture'
        """), params).one() == ("900001", row["HMPG_ADDR"], row["MAIN_IMG"], result.job_id)
        assert db.scalar(text("SELECT error FROM ingestion_jobs WHERE job_id = :id"), {"id": result.job_id}) == [
            {"content_id": "160235", "stage": "culturalEventInfo", "code": "DATE_INVALID"},
        ]

    repeat = run_collection(db_engine, [row, *source_rows])
    assert (repeat.inserted, repeat.updated) == (0, 0)

    # TourAPI가 요금을 제공하면 우선 반영하고, 공식 URL이 계속 비어 있으면 보강값을 유지한다.
    tour_now = NOW + timedelta(days=1)
    new_tour = replace(tour, source_updated_at=tour_now, raw_checksum="tour-updated", admission_fee_text="TourAPI 요금")
    store = FestivalStore(db_engine)
    assert store.finish_job(store.start_job(tour_now), [new_tour], []).updated == 1
    changed_row = {**row, "ORG_LINK": "https://example.invalid/changed", "USE_FEE": "변경 요금"}
    run_collection(db_engine, [changed_row], now=tour_now)
    with db_engine.connect() as db:
        assert db.execute(text("""
            SELECT official_url, admission_fee_text, published_at FROM festivals WHERE festival_id = :id
        """), params).one() == (row["ORG_LINK"], "TourAPI 요금", festival["published_at"])
        assert db.execute(text("""
            SELECT field FROM festival_change_history WHERE festival_id = :id AND source_id = 'seoul_culture'
            ORDER BY field
        """), params).scalars().all() == ["admission_fee_text", "official_url"]


def test_src2_quarantines_missing_and_ambiguous_matches(db_engine, monkeypatch, source_rows):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    seed_tourapi(db_engine)
    seed_tourapi(db_engine, item_id="1234568")
    seed_tourapi(db_engine, item_id="1234569", title="거리가 먼 축제", mapy="37.495")
    rows = [
        festival_row(source_rows[0]),
        festival_row(source_rows[0], item_id="900002", TITLE="처음 본 축제"),
        festival_row(source_rows[0], item_id="900003", TITLE="거리가 먼 축제"),
    ]
    result = run_collection(db_engine, rows)
    assert (result.inserted, result.updated) == (3, 0)
    with db_engine.begin() as db:
        assert db.execute(text("""
            SELECT fs.source_item_id, q.reason, f.review_status, f.published_at, f.source_class_level2
            FROM festival_sources fs JOIN festival_review_queue q USING (festival_id) JOIN festivals f USING (festival_id)
            WHERE fs.source_id = 'seoul_culture' ORDER BY fs.source_item_id
        """)).all() == [
            ("900001", "duplicate", "pending", None, None),
            ("900002", "class_unverified", "pending", None, None),
            ("900003", "duplicate", "pending", None, None),
        ]
        assert db.scalar(text("SELECT count(*) FROM festivals WHERE published_at IS NOT NULL")) == 3
        db.execute(text("""
            UPDATE festival_review_queue SET approval_status = 'rejected' WHERE reason = 'class_unverified'
        """))
    repeat = run_collection(db_engine, rows)
    assert (repeat.inserted, repeat.updated) == (0, 0)
    with db_engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM festival_review_queue")) == 3
        assert db.scalar(text(
            "SELECT approval_status FROM festival_review_queue WHERE reason = 'class_unverified'"
        )) == "rejected"


def test_src2_does_not_fill_admin_locked_null(db_engine, monkeypatch, source_rows):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    festival_id, _ = seed_tourapi(db_engine)
    row = festival_row(source_rows[0])
    params = {"id": festival_id}
    with db_engine.begin() as db:
        db.execute(text("""
            INSERT INTO festival_change_history (festival_id, field, before_value, after_value, actor, changed_at)
            VALUES (:id, 'official_url', '"https://example.invalid/removed"'::jsonb, 'null'::jsonb, 'admin', now())
        """), params)

    first = run_collection(db_engine, [row])
    assert first.updated == 1
    with db_engine.begin() as db:
        assert db.execute(text("""
            SELECT official_url, admission_fee_text FROM festivals WHERE festival_id = :id
        """), params).one() == (None, row["USE_FEE"])
        assert db.execute(text("""
            SELECT reason, proposed_value FROM festival_review_queue WHERE festival_id = :id
        """), params).one() == ("conflict", {"official_url": row["ORG_LINK"]})
        db.execute(text("UPDATE festival_review_queue SET approval_status = 'rejected' WHERE festival_id = :id"), params)

    repeat = run_collection(db_engine, [row])
    assert repeat.updated == 0
    with db_engine.connect() as db:
        assert db.scalar(text("SELECT official_url FROM festivals WHERE festival_id = :id"), params) is None
        assert db.execute(text("SELECT approval_status FROM festival_review_queue")).scalars().all() == ["rejected"]


def test_src2_concurrent_collectors_create_one_quarantine(db_engine, monkeypatch, source_rows):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    row = festival_row(source_rows[0])
    barrier = Barrier(2)

    def run():
        def respond(_):
            barrier.wait(timeout=5)
            return httpx2.Response(200, json=source_body([row]))

        with httpx2.Client(transport=httpx2.MockTransport(respond)) as http:
            return collect.collect_to_db(NOW, locked_engine=db_engine, http_client=http)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run) for _ in range(2)]
        assert sorted(future.result(timeout=10).inserted for future in futures) == [0, 1]
    with db_engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM festivals")) == 1
        assert db.scalar(text("SELECT count(*) FROM festival_sources")) == 1
        assert db.scalar(text("SELECT count(*) FROM festival_review_queue")) == 1


def test_src2_public_endpoints_keep_tourapi_source_and_hide_quarantine(
    app_engine, db_engine, monkeypatch, source_rows, use_user_db,
):
    from api.main import app

    festival_id, _ = seed_tourapi(db_engine)
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", KEY)
    row = festival_row(source_rows[0])
    run_collection(db_engine, [row, festival_row(source_rows[0], item_id="900002", TITLE="새 서울 축제")])
    with db_engine.connect() as db:
        private_id = db.scalar(text("SELECT festival_id FROM festival_review_queue"))

    monkeypatch.setenv("FESTIVAL_DATA", "db")
    use_user_db(app_engine.url)
    with TestClient(app) as client:
        listing = client.get("/api/v1/festivals").json()
        assert [(item["festival_id"], item["source"]) for item in listing["items"]] == [(festival_id, "tourapi")]
        detail = client.get(f"/api/v1/festivals/{festival_id}").json()
        assert (detail["source"], detail["source_ref"], detail["homepage_url"]) == ("tourapi", "1234567", row["ORG_LINK"])
        assert client.get(f"/api/v1/festivals/{private_id}").status_code == 404

    with app_engine.connect() as db:
        assert db.execute(text(
            "SELECT source_item_id FROM festival_sources WHERE source_id = 'seoul_culture'"
        )).scalars().all() == ["900001"]
