"""A83~A85 RAG 공식 문서 검토 — 모의 모드(메모리 저장소)."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from api.mocks import rag_documents as mock_rag
from api.mocks.store import AccessSession, access_sessions
from api.providers.route_base import KST
from api.request_logs import admin_rag_document_endpoint, private_endpoint
from api.schemas.rag_documents import RagDocumentItem

ADMIN = "/api/v1/admin/rag-documents"
FESTIVAL = "fst_000001"


def _item(now, *, source_url="https://example.test/guide", effective_from=None, effective_to=None,
          status="pending", checksum=None, festival_id=FESTIVAL, created=0):
    return RagDocumentItem(
        document_id=uuid4(), festival_id=festival_id, title="공식 안내", category="faq", authored_by="source",
        source_url=source_url, publisher="축제 사무국", published_at=None, effective_from=effective_from,
        effective_to=effective_to, collected_at=now, approval_status=status, approved_by=None, approved_at=None,
        checksum=checksum or uuid4().hex, chunk_count=0, created_at=now + timedelta(seconds=created),
    )


@pytest.fixture
def setup(monkeypatch):
    now = [datetime.now(KST)]
    store = mock_rag.MemoryRagDocumentStore(lambda: now[0])
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    monkeypatch.setattr(mock_rag, "memory_store", store)
    token = uuid4().hex
    monkeypatch.setenv("MOCK_ADMIN_REVIEW_TOKEN", token)
    return store, now, {"Authorization": f"Bearer {token}"}


def test_paths_are_logged_without_document_ids():
    doc = uuid4()
    assert admin_rag_document_endpoint(ADMIN) == ADMIN
    assert admin_rag_document_endpoint(f"{ADMIN}/{doc}") == ADMIN + "/{document_id}"
    assert private_endpoint(f"{ADMIN}/{doc}/review") == ADMIN + "/{document_id}/review"
    assert admin_rag_document_endpoint(f"{ADMIN}/{doc}/other") is None


def test_operator_only_and_state_unchanged_without_permission(client, setup):
    store, now, operator = setup
    doc = _item(now[0])
    store.add(doc, ["본문"])
    url = f"{ADMIN}/{doc.document_id}"
    body = {"decision": "approve", "checksum": doc.checksum}
    assert client.get(ADMIN).status_code == 401
    assert client.post(url + "/review", json=body).status_code == 401
    regular = uuid4().hex
    access_sessions[regular] = AccessSession(str(uuid4()), datetime.now(KST) + timedelta(minutes=1))
    user = {"Authorization": f"Bearer {regular}"}
    assert client.get(ADMIN, headers=user).status_code == 403
    assert client.post(url + "/review", json=body, headers=user).status_code == 403
    assert client.get(url, headers=operator).json()["approval_status"] == "pending"


def test_list_filters_and_detail_without_vectors(client, setup):
    store, now, operator = setup
    pending = _item(now[0], created=2)
    rejected = _item(now[0], status="rejected", created=1)
    other = _item(now[0], festival_id="fst_000002", created=0)
    store.add(pending, ["가" * 300, "둘째 조각"])
    store.add(rejected)
    store.add(other)
    page = client.get(ADMIN, params={"approval_status": "pending", "festival_id": FESTIVAL}, headers=operator)
    assert page.status_code == 200 and page.headers["X-Mock"] == "true"
    assert page.json()["total"] == 1 and page.json()["items"][0]["document_id"] == str(pending.document_id)
    assert page.json()["items"][0]["chunk_count"] == 2
    all_docs = client.get(ADMIN, params={"page_size": 2}, headers=operator).json()
    assert all_docs["total"] == 3 and [i["document_id"] for i in all_docs["items"]] == [
        str(pending.document_id), str(rejected.document_id),
    ]
    detail = client.get(f"{ADMIN}/{pending.document_id}", headers=operator).json()
    assert [c["chunk_index"] for c in detail["chunks"]] == [0, 1]
    assert len(detail["chunks"][0]["preview"]) == 200
    assert "embedding" not in detail["chunks"][0] and detail["events"] == []
    assert client.get(f"{ADMIN}/{uuid4()}", headers=operator).json()["error"]["code"] == "RAG_DOCUMENT_NOT_FOUND"
    assert client.get(ADMIN, params={"approval_status": "done"}, headers=operator).status_code == 422


def test_review_rules_checksum_duplicate_empty_and_rejection(client, setup):
    store, now, operator = setup
    doc = _item(now[0])
    empty = _item(now[0])
    store.add(doc, ["본문"])
    store.add(empty)
    url = f"{ADMIN}/{doc.document_id}/review"
    changed = client.post(url, json={"decision": "approve", "checksum": "different"}, headers=operator)
    assert changed.status_code == 409 and changed.json()["error"]["code"] == "RAG_DOCUMENT_CHANGED"
    no_reason = client.post(url, json={"decision": "reject", "checksum": doc.checksum}, headers=operator)
    assert no_reason.status_code == 422
    assert client.post(f"{ADMIN}/{empty.document_id}/review", json={
        "decision": "approve", "checksum": empty.checksum,
    }, headers=operator).json()["error"]["code"] == "RAG_DOCUMENT_EMPTY"

    approved = client.post(url, json={"decision": "approve", "checksum": doc.checksum}, headers=operator)
    assert approved.status_code == 200
    result = approved.json()
    assert result["approval_status"] == "approved" and result["approved_by"] == str(UUID(int=0))
    assert datetime.fromisoformat(result["approved_at"]) == now[0] and result["superseded_document_ids"] == []
    again = client.post(url, json={"decision": "reject", "checksum": doc.checksum, "reason": "중복"}, headers=operator)
    assert again.status_code == 409 and again.json()["error"]["code"] == "RAG_DOCUMENT_ALREADY_REVIEWED"

    rejected = client.post(f"{ADMIN}/{empty.document_id}/review", json={
        "decision": "reject", "checksum": empty.checksum, "reason": "공식 출처 아님",
    }, headers=operator).json()
    assert rejected["approval_status"] == "rejected" and rejected["approved_by"] is None
    events = client.get(f"{ADMIN}/{empty.document_id}", headers=operator).json()["events"]
    assert [(e["action"], e["reason"]) for e in events] == [("reject", "공식 출처 아님")]


def test_revision_approval_closes_previous_approved_document(client, setup):
    store, now, operator = setup
    starts = now[0] + timedelta(days=1)
    old = _item(now[0], effective_from=now[0] - timedelta(days=3))
    other_url = _item(now[0], source_url="https://example.test/other")
    revision = _item(now[0], effective_from=starts, effective_to=starts + timedelta(days=5))
    for doc in (old, other_url, revision):
        store.add(doc, ["본문"])
    for doc in (old, other_url):
        assert client.post(f"{ADMIN}/{doc.document_id}/review", json={
            "decision": "approve", "checksum": doc.checksum,
        }, headers=operator).status_code == 200

    result = client.post(f"{ADMIN}/{revision.document_id}/review", json={
        "decision": "approve", "checksum": revision.checksum,
    }, headers=operator).json()
    assert result["superseded_document_ids"] == [str(old.document_id)]
    old_detail = client.get(f"{ADMIN}/{old.document_id}", headers=operator).json()
    assert datetime.fromisoformat(old_detail["effective_to"]) == starts
    assert [e["action"] for e in old_detail["events"]] == ["approve", "supersede"]
    assert client.get(f"{ADMIN}/{other_url.document_id}", headers=operator).json()["effective_to"] is None
