from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest

from api.routers.community import companions
from api.services import companion_rules
from api.services.mock_companions import MemoryCompanions

from .test_my_account import register_and_login

POSTS = "/api/v1/companion-posts"
APPLICATIONS = "/api/v1/companion-applications"
FESTIVAL = "fst_000001"
MEET_AT = "2026-11-25T00:15:00+09:00"


@pytest.fixture
def clock(monkeypatch):
    store = MemoryCompanions()
    monkeypatch.setattr(companions, "memory", store)
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    now = [datetime(2026, 11, 24, 13, tzinfo=timezone.utc)]
    monkeypatch.setattr(companion_rules, "now_utc", lambda: now[0])
    return now


def post_body(**changes):
    return {"festival_id": FESTIVAL, "meet_at": MEET_AT, "capacity": 1, "memo": "축제 구경", **changes}


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_mock_post_application_and_place(client, clock):
    owner, _, _ = register_and_login(client, "Owner")
    first, _, _ = register_and_login(client, "First")
    second, _, _ = register_and_login(client, "Second")
    created = client.post(POSTS, headers=owner, json=post_body())
    assert created.status_code == 201 and created.headers["X-Mock"] == "true"
    post_id = created.json()["post_id"]
    detail = f"{POSTS}/{post_id}"
    applications = detail + "/applications"
    place = detail + "/meeting-place"

    listing = client.get(f"/api/v1/festivals/{FESTIVAL}/companion-posts").json()["items"]
    assert [row["post_id"] for row in listing] == [post_id]
    assert listing[0]["author_display_name"] == "Owner"
    assert client.get(f"/api/v1/festivals/{FESTIVAL}/companion-posts?page=2").json() == {"items": []}
    feed = client.get(POSTS).json()
    assert feed["total"] == 1
    assert feed["items"][0]["post_id"] == post_id
    assert feed["items"][0]["festival_id"] == FESTIVAL
    assert feed["items"][0]["festival_name"] == "광화문 겨울빛 축제"
    assert client.get(POSTS, params={"q": "광화문"}).json()["total"] == 1
    assert client.get(POSTS, params={"q": "부산"}).json()["total"] == 0
    public = client.get(detail)
    assert public.json() == {**listing[0], "my_application_status": None}
    assert public.headers["Cache-Control"] == "private, no-store"

    assert_error(client.post(applications, headers=owner), 403, "OWN_POST")
    assert client.get(place, headers=owner).json() == {"status": "undecided"}
    assert_error(client.get(place, headers=first), 403, "FORBIDDEN")
    assert_error(client.put(place, headers=first, json={"name": "정문"}), 403, "FORBIDDEN")
    assert client.put(place, headers=owner, json={"name": "정문", "lat": 37.5}).status_code == 422
    correct = {"name": "정문", "address": "축제 광장"}
    assert client.put(place, headers=owner, json=correct).status_code == 200

    attempted = client.post(applications, headers=first, json={"message": "같이 갈래요"})
    assert attempted.status_code == 201
    application_id = attempted.json()["application_id"]
    assert_error(client.post(applications, headers=first), 409, "APPLICATION_EXISTS")
    assert client.get(detail, headers=first).json()["my_application_status"] == "pending"
    assert_error(client.get(applications, headers=first), 403, "FORBIDDEN")
    assert_error(client.get(place, headers=first), 403, "FORBIDDEN")
    incoming = client.get(applications, headers=owner, params={"status": "pending"}).json()["items"]
    assert incoming == [{
        "application_id": application_id, "applicant_display_name": "First",
        "applicant_age": 26, "applicant_gender": "female", "message": "같이 갈래요",
        "status": "pending", "created_at": "2026-11-24T13:00:00Z",
    }]

    decision = f"{APPLICATIONS}/{application_id}"
    assert_error(client.post(decision + "/approve", headers=second), 403, "FORBIDDEN")
    assert client.post(decision + "/cancel", headers=first).json()["status"] == "cancelled"
    assert client.get(detail, headers=first).json()["my_application_status"] == "cancelled"
    retry = client.post(applications, headers=first).json()["application_id"]
    second_id = client.post(applications, headers=second).json()["application_id"]
    assert retry != application_id
    assert client.post(f"{APPLICATIONS}/{second_id}/reject", headers=owner).json()["status"] == "rejected"
    assert_error(client.post(applications, headers=second), 409, "APPLICATION_EXISTS")
    accepted = client.post(f"{APPLICATIONS}/{retry}/approve", headers=owner)
    assert accepted.json() == {"application_id": retry, "status": "approved", "post_status": "full"}
    assert_error(client.post(f"{APPLICATIONS}/{retry}/cancel", headers=first), 409, "APPLICATION_NOT_PENDING")
    assert client.get(place, headers=first).json()["name"] == "정문"
    assert_error(client.get(place, headers=second), 403, "FORBIDDEN")


def test_mock_edit_close_end_and_retention(client, clock):
    owner, _, _ = register_and_login(client, "Owner")
    other, _, _ = register_and_login(client, "Other")
    row = client.post(POSTS, headers=owner, json=post_body()).json()
    detail = f"{POSTS}/{row['post_id']}"
    place = detail + "/meeting-place"
    assert_error(client.patch(detail, headers=other, json={"memo": "수정"}), 403, "FORBIDDEN")
    assert client.patch(detail, headers=owner, json={}).status_code == 422
    assert client.patch(detail, headers=owner, json={"capacity": None}).status_code == 422
    assert client.patch(detail, headers=owner, json={"capacity": 2, "age_pref": "20s"}).json()["status"] == "open"
    assert client.get(detail).json()["capacity"] == 2
    assert client.put(place, headers=owner, json={"name": "정문"}).status_code == 200
    application_id = client.post(detail + "/applications", headers=other).json()["application_id"]
    assert client.post(detail + "/close", headers=owner).json()["status"] == "full"
    assert_error(client.post(f"{APPLICATIONS}/{application_id}/approve", headers=owner), 409, "POST_CLOSED")
    assert client.patch(detail, headers=owner, json={"capacity": 3}).json()["status"] == "full"
    assert client.post(detail + "/end", headers=owner).json()["status"] == "ended"
    assert_error(client.patch(detail, headers=owner, json={"memo": "수정"}), 409, "POST_CLOSED")
    clock[0] += timedelta(hours=71, minutes=59)
    assert client.get(place, headers=owner).json()["name"] == "정문"
    assert client.get(detail).json()["memo"] == "축제 구경"
    clock[0] += timedelta(minutes=1)
    assert client.get(place, headers=owner).json() == {"status": "undecided"}
    assert client.get(detail).json()["memo"] is None


def test_mock_companion_room_list_uses_current_post_details(client, clock):
    owner, _, _ = register_and_login(client, "Owner")
    member, _, _ = register_and_login(client, "Member")
    created = client.post(POSTS, headers=owner, json=post_body()).json()
    detail = f"{POSTS}/{created['post_id']}"
    application = client.post(f"{detail}/applications", headers=member).json()["application_id"]
    assert client.post(f"{APPLICATIONS}/{application}/approve", headers=owner).status_code == 200
    path = "/api/v1/me/chat-rooms?filter=companion"
    festival_name = client.get(f"/api/v1/festivals/{FESTIVAL}").json()["name"]

    room, = client.get(path, headers=member).json()["items"]
    assert room == {
        "room_id": created["room_id"], "room_type": "companion", "name": None, "status": "active",
        "last_message_at": None, "unread_count": 0, "my_status": "joined",
        "peer_display_name": None, "festival_name": festival_name, "meet_at": MEET_AT,
    }

    changed = (datetime.fromisoformat(MEET_AT) + timedelta(minutes=30)).isoformat()
    assert client.patch(detail, headers=owner, json={"meet_at": changed}).status_code == 200
    assert client.get(path, headers=member).json()["items"][0]["meet_at"] == changed
    with companions.memory.lock:
        companions.memory.posts[created["post_id"]].hidden = True
    assert client.get(path, headers=member).json()["items"] == [{**room, "festival_name": None, "meet_at": None}]
    assert client.get(path, headers=owner).json()["items"] == [{**room, "meet_at": changed}]


def test_mock_validates_kst_schedule_and_auto_ends(client, clock):
    owner, _, _ = register_and_login(client, "Owner")
    assert_error(client.post(POSTS, json=post_body()), 401, "UNAUTHORIZED")
    assert_error(client.post(POSTS, headers=owner, json=post_body(festival_id="fst_missing")), 404, "FESTIVAL_NOT_FOUND")
    for invalid in ("2026-11-24T12:59:59Z", "2026-12-31T15:00:00Z"):
        assert_error(client.post(POSTS, headers=owner, json=post_body(meet_at=invalid)), 400, "MEET_AT_INVALID")
    for changes in (
        {"capacity": 11}, {"capacity": True}, {"meet_at": "2026-11-25T00:15:00"},
        {"memo": "x" * 501}, {"memo": "메모\x00"},
    ):
        assert client.post(POSTS, headers=owner, json=post_body(**changes)).status_code == 422
    assert client.get(f"/api/v1/festivals/{FESTIVAL}/companion-posts?page=0").status_code == 422
    # 14:59 UTC is 23:59 KST on the last day of the festival.
    assert client.post(POSTS, headers=owner, json=post_body(meet_at="2026-12-31T14:59:00Z")).status_code == 201
    first, second, third = [
        POSTS + "/" + client.post(POSTS, headers=owner, json=post_body()).json()["post_id"] for _ in range(3)
    ]
    assert client.post(second + "/cancel", headers=owner).json()["status"] == "cancelled"
    clock[0] = datetime.fromisoformat(MEET_AT) + timedelta(hours=1)
    assert_error(client.post(third + "/cancel", headers=owner), 409, "POST_CLOSED")
    clock[0] += timedelta(hours=11)
    assert client.get(first).json()["status"] == "ended"
    assert client.get(second).json()["status"] == "cancelled"


def test_mock_competing_approvals_observe_one_seat(client, clock):
    owner, _, _ = register_and_login(client, "Owner")
    first, _, _ = register_and_login(client, "First")
    second, _, _ = register_and_login(client, "Second")
    created = client.post(POSTS, headers=owner, json=post_body())
    assert created.status_code == 201
    detail = f"{POSTS}/{created.json()['post_id']}"
    applications = [
        client.post(detail + "/applications", headers=headers).json()["application_id"]
        for headers in (first, second)
    ]
    ready = Barrier(2, timeout=5)

    def approve(application_id):
        ready.wait()
        return client.post(f"{APPLICATIONS}/{application_id}/approve", headers=owner)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(approve, applications))
    assert sorted(response.status_code for response in results) == [200, 409]
    assert_error(next(response for response in results if response.status_code == 409), 409, "CAPACITY_FULL")
    assert client.get(detail).json()["approved_count"] == 1


@pytest.mark.parametrize("author_blocks", [True, False])
def test_blocks_prevent_apply_and_approve_in_either_direction(client, clock, author_blocks):
    from .test_chat import signup

    (author, owner_headers), (applicant, applicant_headers) = [signup(client, i) for i in range(2)]
    first = client.post(POSTS, headers=owner_headers, json=post_body()).json()
    second = client.post(POSTS, headers=owner_headers, json=post_body()).json()
    pending = client.post(f"{POSTS}/{first['post_id']}/applications", headers=applicant_headers).json()
    actor, target = (owner_headers, applicant) if author_blocks else (applicant_headers, author)
    assert client.put(f"/api/v1/me/blocks/{target}", headers=actor).status_code == 200

    assert_error(client.post(f"{POSTS}/{second['post_id']}/applications", headers=applicant_headers), 409, "BLOCKED")
    approve = f"{APPLICATIONS}/{pending['application_id']}/approve"
    assert_error(client.post(approve, headers=owner_headers), 409, "BLOCKED")
    assert client.get(f"{POSTS}/{first['post_id']}", headers=owner_headers).json()["approved_count"] == 0
    assert client.delete(f"/api/v1/me/blocks/{target}", headers=actor).status_code == 204
    assert client.post(approve, headers=owner_headers).json()["status"] == "approved"
