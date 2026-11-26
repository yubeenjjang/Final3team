import asyncio
from datetime import datetime, timedelta

import httpx2
import pytest
from sqlalchemy import text

from api.ingestion.facilities.collect import load_source
from api.ingestion.festivals.normalize import KST
from api.repositories.festival_info import nearby_facility_items

from .test_i12_catalog_db import app_engine  # noqa: F401

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 26, 11, tzinfo=KST)
SERVICE = "busStopLocationXyInfo"
ROWS = [
    {"STOPS_NO": "100000380", "STOPS_NM": "서울역사박물관.경희궁앞", "XCRD": "126.97038", "YCRD": "37.569135",
     "NODE_ID": "01007", "STOPS_TYPE": "중앙차로"},
    {"STOPS_NO": "100000001", "STOPS_NM": "먼 정류장", "XCRD": "127.1", "YCRD": "37.4", "NODE_ID": "01001"},
]


def _run(engine, rows, now=NOW):
    body = {SERVICE: {"RESULT": {"CODE": "INFO-000"}, "list_total_count": len(rows), "row": rows}}
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=body))) as http:
        return load_source(engine, "seoul_bus_stop", now, http_client=http)


@pytest.fixture
def clean(db_engine):
    with db_engine.begin() as db:
        db.execute(text("DELETE FROM facilities WHERE source_id = 'seoul_bus_stop'"))
    yield db_engine
    with db_engine.begin() as db:
        db.execute(text("DELETE FROM facilities WHERE source_id = 'seoul_bus_stop'"))


def test_reload_upserts_without_duplicates_and_a08_reads_it(clean, app_engine, use_user_db, monkeypatch):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", "synthetic-key")
    first = _run(clean, ROWS)
    assert (first.scanned, first.inserted, first.updated, first.rejected) == (2, 2, 0, 0)
    renamed = [{**ROWS[0], "STOPS_NM": "서울역사박물관"}, ROWS[1]]
    second = _run(clean, renamed, NOW + timedelta(days=30))
    assert (second.inserted, second.updated) == (0, 2)
    with clean.connect() as db:
        rows = db.execute(text(
            "SELECT name, ref_code, region_code, source_url FROM facilities WHERE source_id = 'seoul_bus_stop'"
            " ORDER BY source_item_id"
        )).all()
        source = db.execute(text(
            "SELECT scope, status, last_success_at FROM data_sources WHERE source_id = 'seoul_bus_stop'"
        )).one()
        jobs = db.scalar(text("SELECT count(*) FROM ingestion_jobs WHERE source_id = 'seoul_bus_stop'"))
    assert [tuple(row) for row in rows] == [
        ("먼 정류장", "01001", "SEOUL", "https://data.seoul.go.kr"),
        ("서울역사박물관", "01007", "SEOUL", "https://data.seoul.go.kr"),
    ]
    assert source.scope == "seoul_only" and source.status == "verified"
    assert source.last_success_at == NOW + timedelta(days=30)
    assert jobs == 2
    # A08은 앱 계정(noldaga_app)으로 읽는다: 공개 정책으로 보여야 한다.
    use_user_db(app_engine.url.set(drivername="postgresql+psycopg"))
    nearby = asyncio.run(nearby_facility_items(37.5692, 126.9776, 1000, ["bus_stop"]))
    assert [item.name for item in nearby] == ["서울역사박물관"]


def test_failed_listing_keeps_existing_rows(clean, monkeypatch):
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", "synthetic-key")
    _run(clean, ROWS)
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(503))) as http:
        with pytest.raises(RuntimeError):
            load_source(clean, "seoul_bus_stop", NOW, http_client=http)
    with clean.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM facilities WHERE source_id = 'seoul_bus_stop'")) == 2
        assert db.scalar(text(
            "SELECT count(*) FROM ingestion_jobs WHERE source_id = 'seoul_bus_stop' AND status = 'failed'"
        )) == 1
