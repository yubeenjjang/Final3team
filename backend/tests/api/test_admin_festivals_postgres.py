from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from api.ingestion.festivals.normalize import normalize_festival
from api.ingestion.festivals.store import FestivalStore
from api.ingestion.tourapi_snapshot import ingest
from shared.db import session as sessions

from .test_admin_festivals import BODY, PATH
from .test_admin_review_postgres import review_database

pytestmark = pytest.mark.db


def test_a55_a56_roles_rls_audit_concurrent_registration_and_publish(client, review_database):
    engine, headers, roles, _, _ = review_database
    name = f"관리자 시험 {uuid4().hex}"
    payload = BODY | {"name": name, "overview": "등록 소개"}
    key = {"name": name}

    async def check_rls(festival_id, visible):
        async with sessions.user_db_session(roles["user"]) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            assert await db.scalar(
                text("SELECT count(*) FROM public.profiles WHERE user_id = :id"), {"id": roles["admin"]},
            ) == 0
            assert await db.scalar(
                text("SELECT count(*) FROM public.festivals WHERE festival_id = :id"), {"id": festival_id},
            ) == int(visible)
            for table in ("festival_review_queue", "festival_change_history"):
                with pytest.raises(DBAPIError) as error:
                    async with db.begin_nested():
                        await db.execute(text(f"SELECT festival_id FROM public.{table} WHERE festival_id = :id"),
                                         {"id": festival_id})
                assert error.value.orig.sqlstate == "42501"

    assert client.post(PATH, json=payload).status_code == 401
    for role in ("operator", "user"):
        assert client.post(PATH, headers=headers[role], json=payload).status_code == 403

    def race(action, changes):
        barrier = Barrier(2, timeout=10)

        def request(fields):
            barrier.wait()
            return action(fields)

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(request, changes))

    try:
        registered = race(lambda body: client.post(PATH, headers=headers["admin"], json=body), [payload, payload])
        assert sorted(response.status_code for response in registered) == [201, 409]
        assert all("X-Mock" not in response.headers for response in registered)
        festival_id = next(response.json()["festival_id"] for response in registered if response.status_code == 201)
        client.portal.call(check_rls, festival_id, False)
        duplicate = client.post(PATH, headers=headers["admin"], json=payload)
        assert duplicate.json()["error"]["code"] == "DUPLICATE_FESTIVAL"
        queue = client.get(f"{PATH}/review-queue", headers=headers["operator"], params={"reason": "duplicate"})
        assert sum(row["festival_id"] == festival_id for row in queue.json()["items"]) == 1
        patch_path = f"{PATH}/{festival_id}"
        assert client.patch(patch_path, headers=headers["operator"], json={"reason": "공개", "published": True}).status_code == 403

        updates = race(
            lambda fields: client.patch(patch_path, headers=headers["admin"], json={
                "reason": "게시 및 추가 확인", "published": True,
            } | fields),
            [{"overview": "수정 소개"}, {"end_date": "2026-12-05"}],
        )
        assert all(response.status_code == 200 for response in updates)
        assert updates[0].json() == updates[1].json()
        assert updates[0].json()["published_at"]
        client.portal.call(check_rls, festival_id, True)

        with engine.connect() as db:
            params = {"id": festival_id}
            assert db.execute(text("""
                SELECT category, source_class_level2, summary, end_date
                FROM public.festivals WHERE festival_id = :id
            """), params).one() == ("festival", "EV01", "수정 소개", date(2026, 12, 5))
            assert db.scalar(text("""
                SELECT source_id FROM public.festival_sources WHERE festival_id = :id
            """), params) == "admin_manual"
            audit = db.execute(text("""
                SELECT field, before_value, after_value, actor, actor_user_id
                FROM public.festival_change_history WHERE festival_id = :id AND reason = '게시 및 추가 확인'
            """), params).all()
            assert len(audit) == 4
            assert {row.field for row in audit} == {"summary", "end_date", "review_status", "published_at"}
            assert all(row.actor == "admin" and row.actor_user_id == roles["admin"] for row in audit)
            assert next(row for row in audit if row.field == "summary")[1:3] == ("등록 소개", "수정 소개")

        hidden = client.patch(patch_path, headers=headers["admin"], json={"published": False, "reason": "숨김"})
        assert hidden.json() == {"festival_id": festival_id, "review_status": "hidden", "published_at": None}
        client.portal.call(check_rls, festival_id, False)
    finally:
        with engine.begin() as db:
            for table in ("festival_review_queue", "festival_change_history", "festival_sources"):
                db.execute(text(f"""
                    DELETE FROM public.{table}
                    WHERE festival_id IN (SELECT festival_id FROM public.festivals WHERE title = :name)
                """), key)
            db.execute(text("DELETE FROM public.festivals WHERE title = :name"), key)


def test_both_collectors_preserve_admin_edits_and_queue_latest_conflict(client, review_database):
    engine, headers, _, _, _ = review_database
    item_id = str(uuid4().int)[:15]
    job_ids = []
    festival_id = None
    store = FestivalStore(engine)
    now = datetime.now(timezone.utc)
    item = {
        "contentid": item_id, "title": "공급원 이름", "lDongRegnCd": "11", "lclsSystm2": "EV01",
        "eventstartdate": "20261201", "eventenddate": "20261203", "modifiedtime": "20261121130000",
        "mapy": "37.5", "mapx": "127.1", "addr1": "서울특별시 종로구",
    }

    def collect(raw, overview):
        started_at = datetime.now(timezone.utc)
        job_id = store.start_job(started_at)
        job_ids.append(job_id)
        record = normalize_festival(raw, common={"overview": overview}, today=now.date())
        return store.finish_job(job_id, [record], [])

    try:
        assert collect(item, "공급원 소개").inserted == 1
        with engine.connect() as db:
            festival_id = db.scalar(text("""
                SELECT festival_id FROM public.festival_sources WHERE source_id = 'tourapi' AND source_item_id = :id
            """), {"id": item_id})
        response = client.patch(f"{PATH}/{festival_id}", headers=headers["admin"], json={
            "name": "관리자 확인 이름", "lat": 37.6, "reason": "공식 자료로 정정",
        })
        assert response.status_code == 200
        assert collect(item | {"title": "공급원 변경 이름", "mapy": "37.7", "mapx": "127.2",
                               "modifiedtime": "20261122130000"}, "새 소개").updated == 1

        with engine.connect() as db:
            row = db.execute(text("SELECT * FROM public.festivals WHERE festival_id = :id"),
                             {"id": festival_id}).mappings().one()
        assert row["title"] == "관리자 확인 이름" and row["summary"] == "새 소개"
        assert (float(row["latitude"]), float(row["longitude"]), row["coords_source"]) == (37.6, 127.1, None)

        with Session(engine) as db, db.begin():
            ingest(db, [({**row, "title": "증빙 변경 이름", "source_item_id": item_id,
                          "source_fetched_at": now}, "snapshot-test")], [])
            job_ids.append(db.scalar(text("""
                SELECT last_job_id FROM public.festival_sources WHERE source_id = 'tourapi' AND source_item_id = :id
            """), {"id": item_id}))
            assert db.scalar(text("SELECT title FROM public.festivals WHERE festival_id = :id"),
                             {"id": festival_id}) == "관리자 확인 이름"
            proposals = db.scalars(text("""
                SELECT proposed_value FROM public.festival_review_queue
                WHERE festival_id = :id AND reason = 'conflict' AND approval_status = 'pending'
            """), {"id": festival_id}).all()
            assert proposals == [{"title": "증빙 변경 이름", "latitude": 37.7, "longitude": 127.2,
                                  "coords_source": "tourapi"}]
    finally:
        with engine.begin() as db:
            for table in ("festival_review_queue", "festival_change_history", "festival_sources", "festivals"):
                db.execute(text(f"DELETE FROM public.{table} WHERE festival_id = :id"), {"id": festival_id})
            db.execute(text("DELETE FROM public.ingestion_jobs WHERE job_id = ANY(:ids)"), {"ids": job_ids})
