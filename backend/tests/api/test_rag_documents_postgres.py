"""A83~A85 RAG 공식 문서 검토 — 실제 PostgreSQL(029 적용 일회용 DB).

W27 계약 4절 수용 시험: 승인 전 비노출·승인 후 노출·반려·중복 승인·checksum 불일치·권한 없음 불변·
개정본 승인 시 이전 승인본 effective_to 닫힘. 검색 조건은 dayoung `agents/rag/search.py`의 SEARCH_SQL과 같다.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth.tokens import issue_access_token
from api.ingestion.db import create_ingestion_engine
from api.providers.route_base import KST
from shared.db import session as sessions

pytestmark = pytest.mark.db
ADMIN = "/api/v1/admin/rag-documents"
MODEL, VERSION = "text-embedding-3-small", "v1"
# agents/rag/search.py SEARCH_SQL과 같은 노출 조건(벡터 정렬만 생략)
_SEARCHABLE = text("""
    SELECT c.document_id FROM public.rag_chunks c
    JOIN public.rag_documents d ON d.document_id = c.document_id
    WHERE d.approval_status = 'approved' AND d.festival_id = :festival_id
      AND (d.effective_from IS NULL OR d.effective_from <= :as_of)
      AND (d.effective_to IS NULL OR :as_of < d.effective_to)
      AND c.embedding_model = :model AND c.embedding_version = :version
    ORDER BY c.document_id
""")


def test_postgres_rag_document_review_contract(client, monkeypatch):
    url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    service_engine = create_ingestion_engine(url)
    app_engine = create_ingestion_engine(app_url)
    user_engine = create_async_engine(app_url, hide_parameters=True)

    @event.listens_for(service_engine, "begin")
    def set_service_role(connection):
        connection.exec_driver_sql("SET LOCAL ROLE noldaga_service")

    if not os.environ.get("TEST_DB_APP_URL"):
        @event.listens_for(app_engine, "begin")
        @event.listens_for(user_engine.sync_engine, "begin")
        def set_app_role(connection):
            connection.exec_driver_sql("SET LOCAL ROLE noldaga_app")

    monkeypatch.setattr(sessions, "_service_engine", lambda: service_engine)
    monkeypatch.setattr(sessions, "_user_engine", lambda: user_engine)
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setenv("JWT_SECRET", "rag-review-db-fixture-signing-value-for-tests")

    actors = {"operator": uuid4(), "admin": uuid4(), "user": uuid4()}
    festival_id = "fst_" + uuid4().hex[:20]
    hidden_festival = "fst_" + uuid4().hex[:20]
    now = datetime.now(KST)
    source = "https://example.test/official/" + uuid4().hex
    docs = {name: uuid4() for name in ("old", "revision", "rejected", "empty", "hidden")}

    def headers(role):
        # 토큰 role과 관계없이 RLS 세션에서 읽은 profiles.role로 권한을 판정한다.
        return {"Authorization": f"Bearer {issue_access_token(actors[role], 'admin', now, 300)}"}

    def searchable(as_of):
        with service_engine.connect() as db:
            return set(db.execute(_SEARCHABLE, {
                "festival_id": festival_id, "as_of": as_of, "model": MODEL, "version": VERSION,
            }).scalars())

    def review(name, role="operator", **body):
        body.setdefault("decision", "approve")
        body.setdefault("checksum", "sum-" + name)
        return client.post(f"{ADMIN}/{docs[name]}/review", json=body, headers=headers(role))

    try:
        with service_engine.begin() as db:
            for role, user_id in actors.items():
                db.execute(text("INSERT INTO public.users (user_id, email, password_hash) VALUES (:id, :e, '!')"),
                           {"id": user_id, "e": f"{user_id}@example.test"})
                db.execute(text("INSERT INTO public.profiles (user_id, role) VALUES (:id, :role)"),
                           {"id": user_id, "role": role})
            db.execute(text("""
                INSERT INTO public.festivals
                  (festival_id, title, region_code, category, source_class_level2, review_status, published_at)
                VALUES (:a, '합성 축제', 'SEOUL', 'festival', 'EV01', 'approved', now()),
                       (:b, '비공개 축제', 'SEOUL', 'festival', 'EV01', 'pending', NULL)
            """), {"a": festival_id, "b": hidden_festival})
            starts = now + timedelta(days=1)
            rows = {
                "old": (festival_id, source, now - timedelta(days=3), None),
                "revision": (festival_id, source, starts, starts + timedelta(days=5)),
                "rejected": (festival_id, source + "/x", None, None),
                "empty": (festival_id, source + "/y", None, None),
                "hidden": (hidden_festival, source, None, None),
            }
            for name, (fid, src, eff_from, eff_to) in rows.items():
                db.execute(text("""
                    INSERT INTO public.rag_documents (document_id, festival_id, title, category, source_url, publisher,
                      effective_from, effective_to, collected_at, checksum)
                    VALUES (:id, :fid, '공식 안내', 'faq', :src, '축제 사무국', :ef, :et, now(), :sum)
                """), {"id": docs[name], "fid": fid, "src": src, "ef": eff_from, "et": eff_to, "sum": "sum-" + name})
                if name != "empty":
                    db.execute(text("""
                        INSERT INTO public.rag_chunks (chunk_id, document_id, chunk_index, content, embedding,
                          embedding_model, embedding_version)
                        VALUES (:cid, :id, 0, '반려견 동반 가능', array_fill(0.01::real, ARRAY[1024])::vector, :m, :v)
                    """), {"cid": uuid4(), "id": docs[name], "m": MODEL, "v": VERSION})

        # 승인 전: 검색 비노출, 권한 없는 요청은 상태 불변
        assert searchable(now) == set()
        assert client.get(ADMIN).status_code == 401
        assert review("old", role="user").status_code == 403
        listed = client.get(ADMIN, params={"festival_id": festival_id, "approval_status": "pending"},
                            headers=headers("operator"))
        assert listed.status_code == 200 and "X-Mock" not in listed.headers
        assert listed.json()["total"] == 4
        detail = client.get(f"{ADMIN}/{docs['old']}", headers=headers("operator")).json()
        assert detail["approval_status"] == "pending" and detail["chunk_count"] == 1
        assert detail["chunks"][0]["preview"] == "반려견 동반 가능" and "embedding" not in detail["chunks"][0]

        # 앱 계정은 문서·이력을 읽거나 승인할 수 없다.
        with app_engine.begin() as db:
            assert not db.scalar(text("SELECT has_table_privilege('public.rag_document_events', 'SELECT')"))
            assert not db.scalar(text("SELECT has_table_privilege('public.rag_documents', 'UPDATE')"))

        # checksum 불일치·본문 없음·비공개 축제는 409, 상태 불변
        assert review("old", checksum="tampered").json()["error"]["code"] == "RAG_DOCUMENT_CHANGED"
        assert review("empty").json()["error"]["code"] == "RAG_DOCUMENT_EMPTY"
        assert review("hidden").json()["error"]["code"] == "RAG_FESTIVAL_NOT_PUBLIC"

        # 동시 승인: 하나만 성공하고 나머지는 이미 처리됨
        barrier = Barrier(2, timeout=5)

        def approve_old(role):
            barrier.wait()
            return review("old", role=role)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(approve_old, ("operator", "admin")))
        assert sorted(r.status_code for r in results) == [200, 409]
        winner = next(r for r in results if r.status_code == 200).json()
        assert winner["approval_status"] == "approved" and winner["approved_at"] is not None
        assert winner["approved_by"] in {str(actors["operator"]), str(actors["admin"])}
        assert next(r for r in results if r.status_code == 409).json()["error"]["code"] == "RAG_DOCUMENT_ALREADY_REVIEWED"
        assert searchable(now) == {docs["old"]}

        # 반려: 사유 필수, 반려된 문서는 검색되지 않음
        assert review("rejected", decision="reject").status_code == 422
        assert review("rejected", decision="reject", reason="공식 출처 아님").json()["approval_status"] == "rejected"
        assert docs["rejected"] not in searchable(now)

        # 개정본 승인: 기존 승인본은 새 문서 효력 시작에서 닫히고 두 승인본이 겹치지 않는다.
        revised = review("revision", role="admin").json()
        assert revised["superseded_document_ids"] == [str(docs["old"])]
        assert searchable(now) == {docs["old"]}
        assert searchable(starts) == {docs["revision"]}
        assert searchable(starts - timedelta(microseconds=1)) == {docs["old"]}
        with service_engine.connect() as db:
            closed = db.scalar(text("SELECT effective_to FROM public.rag_documents WHERE document_id = :id"),
                               {"id": docs["old"]})
            assert closed == starts
            events = db.execute(text("""
                SELECT document_id, action, actor FROM public.rag_document_events
                WHERE document_id = ANY(:ids) ORDER BY event_id
            """), {"ids": list(docs.values())}).all()
            assert [(e.document_id, e.action) for e in events] == [
                (docs["old"], "approve"), (docs["rejected"], "reject"),
                (docs["old"], "supersede"), (docs["revision"], "approve"),
            ]
            assert events[-1].actor == actors["admin"]
            with pytest.raises(Exception):
                with service_engine.begin() as tx:
                    tx.execute(text("DELETE FROM public.rag_document_events WHERE document_id = :id"),
                               {"id": docs["old"]})
        history = client.get(f"{ADMIN}/{docs['old']}", headers=headers("operator")).json()["events"]
        assert [e["action"] for e in history] == ["approve", "supersede"]
    finally:
        # 동시 요청 시험에 커밋이 필요하므로 일회용 DB가 정리한다.
        client.portal.call(user_engine.dispose)
        app_engine.dispose()
        service_engine.dispose()
