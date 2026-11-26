from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from sqlalchemy import Engine, text

from api.ingestion.festivals.normalize import KST, FestivalRecord, normalize_festival
from api.ingestion.festivals.store import (
    ErrorEntry,
    FestivalStore,
    changed_fields,
    festival_values,
    upsert_action,
)

NOW = datetime(2026, 11, 23, 12, tzinfo=KST)


@pytest.fixture
def record() -> FestivalRecord:
    return normalize_festival({
        "contentid": "3379778", "title": "가락 옥토버페스트", "lDongRegnCd": "11",
        "eventstartdate": "20261016", "eventenddate": "20261018",
        "mapx": "127.118462", "mapy": "37.494505", "modifiedtime": "20261006091502",
        "lclsSystm1": "EV", "lclsSystm2": "EV01", "lclsSystm3": "EV010600",
    }, today=NOW.date(), details_requested=False)


@pytest.mark.parametrize(
    ("stored", "incoming", "action"),
    [(None, "new", "inserted"), ("same", "same", "unchanged"), ("old", "new", "updated")],
)
def test_I10_upsert_action(stored: str | None, incoming: str, action: str) -> None:
    assert upsert_action(stored, incoming) == action


def test_I10_diff_tracks_only_changed_fields(record: FestivalRecord) -> None:
    stored = festival_values(record, {}, NOW)
    edited = replace(record, title="수정한 축제")
    assert changed_fields(stored, festival_values(edited, stored, NOW)) == {"title": "수정한 축제"}


@pytest.mark.parametrize(
    ("publishable", "review", "published", "expected"),
    [
        (True, "pending", None, ("approved", NOW)),
        (True, "approved", NOW - timedelta(days=1), ("approved", NOW - timedelta(days=1))),
        (False, "approved", NOW, ("pending", None)),
        (True, "hidden", None, ("hidden", None)),
    ],
)
def test_I10_publication_rule(
    record: FestivalRecord,
    publishable: bool,
    review: str,
    published: datetime | None,
    expected: tuple[str, datetime | None],
) -> None:
    incoming = replace(record, publishable=publishable)
    values = festival_values(incoming, {"review_status": review, "published_at": published}, NOW)
    assert (values["review_status"], values["published_at"]) == expected


@pytest.mark.parametrize("category", ["performance", "event", "unknown"])
def test_I19_nonfestival_cannot_publish(record: FestivalRecord, category: str) -> None:
    incoming = replace(record, category=category)
    for review, expected in (("approved", ("pending", None)), ("hidden", ("hidden", NOW))):
        values = festival_values(incoming, {"review_status": review, "published_at": NOW}, NOW)
        assert (values["review_status"], values["published_at"]) == expected


@pytest.mark.db
def test_I10_insert_rerun_update_history_and_hidden(db_engine: Engine, record: FestivalRecord) -> None:
    store = FestivalStore(db_engine)
    pending = replace(
        record, source_item_id="2", latitude=None, longitude=None, coords_source=None,
        publishable=False, review_status="pending",
    )
    first_id = store.start_job(NOW)
    with db_engine.connect() as connection:
        assert connection.execute(text("SELECT status FROM ingestion_jobs")).scalar_one() == "running"
    first = store.finish_job(first_id, [record, pending], [])
    assert (first.status, first.scanned, first.inserted, first.updated, first.rejected) == (
        "success", 2, 2, 0, 0,
    )
    with db_engine.connect() as connection:
        festival_id, collected_at, published_at = connection.execute(text(
            "SELECT festival_id, collected_at, published_at FROM festivals WHERE review_status = 'approved'"
        )).one()
        assert published_at == collected_at
        assert connection.execute(text(
            "SELECT published_at FROM festivals WHERE review_status = 'pending'"
        )).scalar_one() is None
        source = connection.execute(text(
            "SELECT name, provider_org, scope, is_realtime, refresh_s, key_site, status, last_success_at "
            "FROM data_sources WHERE source_id = 'tourapi'"
        )).one()
        assert source[:7] == ("한국관광공사 TourAPI", "한국관광공사", "national", False, 86400, "data.go.kr", "verified")
        assert source.last_success_at == connection.execute(text(
            "SELECT ended_at FROM ingestion_jobs WHERE job_id = :job_id"
        ), {"job_id": first_id}).scalar_one()

    second_id = store.start_job(NOW)
    same_checksum = replace(record, title="저장되지 않는 제목")
    second = store.finish_job(second_id, [same_checksum, pending], [])
    assert (second.status, second.inserted, second.updated) == ("success", 0, 0)
    with db_engine.begin() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM ingestion_jobs")).scalar_one() == 2
        assert connection.execute(text("SELECT COUNT(*) FROM festivals")).scalar_one() == 2
        assert connection.execute(text("SELECT COUNT(*) FROM festival_change_history")).scalar_one() == 0
        current = connection.execute(text(
            "SELECT fs.festival_id, f.title, f.collected_at, f.last_synced_at, fs.fetched_at, fs.last_job_id "
            "FROM festival_sources fs JOIN festivals f USING (festival_id) WHERE fs.source_item_id = :item"
        ), {"item": record.source_item_id}).one()
        assert current[:3] == (festival_id, record.title, collected_at)
        assert current.last_synced_at == current.fetched_at >= collected_at
        assert current.last_job_id == second_id
        connection.execute(text(
            "UPDATE festivals SET review_status = 'hidden', published_at = NULL WHERE festival_id = :festival_id"
        ), {"festival_id": festival_id})

    updated = replace(record, title="수정한 축제", raw_checksum="changed")
    third = store.finish_job(store.start_job(NOW), [updated], [])
    assert (third.inserted, third.updated) == (0, 1)
    with db_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT title, review_status, published_at FROM festivals WHERE festival_id = :festival_id"
        ), {"festival_id": festival_id}).one() == (updated.title, "hidden", None)
        assert connection.execute(text(
            "SELECT festival_id, field, before_value, after_value, actor, source_id FROM festival_change_history"
        )).one() == (festival_id, "title", record.title, updated.title, "ingestion", "tourapi")


@pytest.mark.db
def test_I10_bad_record_rolls_back_its_savepoint(db_engine: Engine, record: FestivalRecord) -> None:
    store = FestivalStore(db_engine)
    invalid_image = replace(record, source_item_id="invalid", image_url="https://example.invalid/image")
    missing_region = replace(record, source_item_id="unknown", region_code=None, publishable=False)
    errors: list[ErrorEntry] = []
    result = store.finish_job(store.start_job(NOW), [invalid_image, missing_region, record], errors)
    assert (result.status, result.scanned, result.inserted, result.updated, result.rejected) == (
        "partial", 3, 1, 0, 2,
    )
    assert [error["code"] for error in errors] == ["DB_INVALID_RECORD", "DB_REQUIRED_FIELD"]
    with db_engine.connect() as connection:
        assert connection.execute(text("SELECT source_item_id FROM festival_sources")).scalar_one() == record.source_item_id
        assert connection.execute(text("SELECT COUNT(*) FROM festivals")).scalar_one() == 1
        assert connection.execute(text("SELECT error FROM ingestion_jobs")).scalar_one() == errors


@pytest.mark.db
def test_W100_admin_cancellation_survives_source_refresh(db_engine: Engine, record: FestivalRecord) -> None:
    store = FestivalStore(db_engine)
    assert store.finish_job(store.start_job(NOW), [record], []).inserted == 1
    with db_engine.begin() as connection:
        festival_id = connection.scalar(text(
            "SELECT festival_id FROM festival_sources WHERE source_id = 'tourapi'"
        ))
        connection.execute(text(
            "UPDATE festivals SET event_status = 'cancelled' WHERE festival_id = :id"
        ), {"id": festival_id})
        connection.execute(text("""
            INSERT INTO festival_change_history
                (festival_id, field, before_value, after_value, actor, changed_at)
            VALUES (:id, 'event_status', '"ended"'::jsonb, '"cancelled"'::jsonb, 'admin', now())
        """), {"id": festival_id})

    changed = replace(record, title="공급원에서 바뀐 제목", raw_checksum="new-checksum")
    assert store.finish_job(store.start_job(NOW + timedelta(days=1)), [changed], []).updated == 1
    with db_engine.connect() as connection:
        assert connection.execute(text(
            "SELECT title, event_status FROM festivals WHERE festival_id = :id"
        ), {"id": festival_id}).one() == (changed.title, "cancelled")
        assert connection.scalar(text("""
            SELECT proposed_value->>'event_status' FROM festival_review_queue
            WHERE festival_id = :id AND reason = 'conflict' AND approval_status = 'pending'
        """), {"id": festival_id}) == "ended"
