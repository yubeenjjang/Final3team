from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest

from api.mocks.admin_festivals import mock_festival_store
from api.mocks.store import AccessSession, access_sessions

PATH = "/api/v1/admin/festivals"
PUBLIC = "/api/v1/festivals"
BODY = {
    "name": "새로운 겨울 축제", "region_code": "SEOUL", "start_date": "2026-12-01",
    "end_date": "2026-12-03", "venue_name": "겨울 광장", "lat": 37.5, "lng": 127.0,
    "address": "서울특별시 종로구 세종대로 172", "reason": "공식 일정 확인",
}


@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    token = uuid4().hex
    monkeypatch.setenv("MOCK_ADMIN_FESTIVALS_TOKEN", token)
    return {"Authorization": f"Bearer {token}"}


def test_admin_only_and_missing_festival(client, admin, monkeypatch):
    token = uuid4().hex
    monkeypatch.setenv("MOCK_ADMIN_REVIEW_TOKEN", token)
    operator = {"Authorization": f"Bearer {token}"}
    token = uuid4().hex
    access_sessions[token] = AccessSession(str(uuid4()), datetime.now(timezone.utc) + timedelta(minutes=1))
    regular = {"Authorization": f"Bearer {token}"}
    for headers, status in (({}, 401), (operator, 403), (regular, 403)):
        assert client.post(PATH, headers=headers, json=BODY).status_code == status
        patch = client.patch(f"{PATH}/fst_000001", headers=headers, json={"published": True, "reason": "확인"})
        assert patch.status_code == status
    missing = client.patch(f"{PATH}/fst_missing", headers=admin, json={"published": True, "reason": "확인"})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"
    non_festival = client.patch(f"{PATH}/fst_REVIEW3", headers=admin, json={"published": True, "reason": "확인"})
    assert non_festival.status_code == 422


@pytest.mark.parametrize("invalid", [
    {"name": "  "}, {"reason": ""}, {"region_code": "ALL"}, {"start_date": "2026-12-04"},
    {"end_date": "2026-02-30"}, {"end_date": 0}, {"lat": 40}, {"lat": "37.5"}, {"lng": 123},
    {"address": " "}, {"address": "서울\n부산"}, {"category": "performance"},
    {"image_url": "https://example.test/picture.jpg"},
    {"image_copyright": {"type": "Type2"}}, {"published": True},
])
def test_registration_validation(client, admin, invalid):
    response = client.post(PATH, headers=admin, json=BODY | invalid)
    assert response.status_code == 422 and response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert mock_festival_store.audit == []


def test_register_patch_publish_and_hide(client, admin):
    registered = client.post(PATH, headers=admin, json=BODY | {
        "overview": "겨울 프로그램", "fee_text": "무료", "homepage_url": "https://example.test/",
        "image_url": "https://example.test/picture.jpg", "thumbnail_url": "https://example.test/thumb.jpg",
        "image_copyright": {"type": "Type3", "modify_allowed": False},
    })
    assert registered.status_code == 201 and registered.headers["X-Mock"] == "true"
    festival_id = registered.json()["festival_id"]
    assert registered.json() == {"festival_id": festival_id, "review_status": "pending"}
    detail_path = f"{PUBLIC}/{festival_id}"
    assert client.get(detail_path).status_code == 404
    patch_path = f"{PATH}/{festival_id}"

    for invalid in ({"end_date": "2026-11-30"}, {"lat": None}, {"image_copyright": None},
                    {"published": "true"}, {"published": None}, {}):
        response = client.patch(patch_path, headers=admin, json={"reason": "수정"} | invalid)
        assert response.status_code == 422 and response.json()["error"]["code"] == "VALIDATION_ERROR"

    result = client.patch(patch_path, headers=admin, json={
        "published": True, "end_date": "2026-12-05", "reason": "기간 정정",
    })
    published = result.json()
    assert result.status_code == 200 and published["review_status"] == "approved" and published["published_at"]
    detail = client.get(detail_path).json()
    assert (detail["source"], detail["source_ref"], detail["end_date"]) == ("admin", festival_id, "2026-12-05")
    assert detail["source"] == client.get(PUBLIC, params={"q": BODY["name"]}).json()["items"][0]["source"]
    assert (detail["overview"], detail["fee_text"], detail["image_copyright"]["type"]) == (
        "겨울 프로그램", "무료", "Type3",
    )
    assert client.patch(patch_path, headers=admin, json={"published": True, "reason": "재시도"}).json() == published
    records = {item["field"]: item for item in mock_festival_store.audit if item["reason"] == "기간 정정"}
    assert set(records) == {"end_date", "review_status", "published_at"}
    assert records["end_date"]["before_value"] == BODY["end_date"]
    assert records["end_date"]["after_value"] == "2026-12-05"
    assert all(item["actor_user_id"] == UUID(int=1) and item["actor"] == "admin" for item in records.values())
    assert not any(item["reason"] == "재시도" for item in mock_festival_store.audit)

    hidden = client.patch(patch_path, headers=admin, json={"published": False, "reason": "숨김"}).json()
    assert hidden == {"festival_id": festival_id, "review_status": "hidden", "published_at": None}
    assert client.get(detail_path).status_code == 404
    assert client.patch(patch_path, headers=admin, json={"published": True, "reason": "재게시"}).json() == published


def test_concurrent_registration_links_existing_festival_to_a24(client, admin):
    barrier = Barrier(2, timeout=5)

    def register():
        barrier.wait()
        return client.post(PATH, headers=admin, json=BODY)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = [pool.submit(register) for _ in range(2)]
        success, duplicate = sorted((future.result() for future in responses), key=lambda item: item.status_code)
    assert (success.status_code, duplicate.status_code) == (201, 409)
    assert duplicate.json()["error"]["code"] == "DUPLICATE_FESTIVAL"
    assert client.post(PATH, headers=admin, json=BODY | {"name": f" {BODY['name']} "}).status_code == 409
    festival_id = success.json()["festival_id"]
    items = client.get(f"{PATH}/review-queue", headers=admin, params={"reason": "duplicate"}).json()["items"]
    matches = [item for item in items if item["festival_id"] == festival_id]
    assert len(matches) == 1 and matches[0]["proposed_value"]["title"] == BODY["name"]
    decision = client.post(f"{PATH}/review-queue", headers=admin, json={
        "queue_id": matches[0]["queue_id"], "decision": "approve", "note": "등록 자료 검토",
    })
    assert decision.status_code == 200
    assert client.get(f"{PUBLIC}/{festival_id}").status_code == 200
