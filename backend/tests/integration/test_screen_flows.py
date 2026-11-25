import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from api.auth.tokens import refresh_hash
from api.ingestion.festivals.normalize import KST
from api.ingestion.festivals.store import JobResult
from api.jobs import scheduler
from api.jobs.assistant_queue import PostgresAssistantQueue
from api.jobs.assistant_runner import AgentResult
from api.jobs.assistant_worker import work_once
from shared.db.session import user_db_session

from .conftest import auth_header, checked

pytestmark = pytest.mark.db

API = "/api/v1"
AUTH = f"{API}/auth"
FAVORITES = f"{API}/me/favorites"
FRIEND_REQUESTS = f"{API}/friend-requests"
ROOMS = f"{API}/chat-rooms"
POSTS = f"{API}/companion-posts"
ADMIN_REPORTS = f"{API}/admin/reports"


def rls_count(browser, user, sql, **params):
    async def count():
        async with user_db_session(user.user_id) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            return await db.scalar(text(sql), params)

    return browser.run(count)


def friend_request(request, sender, recipient):
    created = request("POST", FRIEND_REQUESTS, headers=sender.headers,
                      json={"to_user_id": str(recipient.user_id)})
    body = checked(created, 201)
    assert body["status"] == "pending"
    return body["request_id"]


def accept_friend(request, recipient, request_id):
    accepted = request("POST", f"{FRIEND_REQUESTS}/{request_id}/accept", headers=recipient.headers)
    assert checked(accepted, 200) == {"request_id": request_id, "status": "accepted"}


def direct_body(friend):
    return {"type": "direct", "friend_id": str(friend.user_id)}


def send_messages(browser, sender, room, *messages):
    ticket = checked(browser.request("POST", f"{API}/ws-tickets", headers=sender.headers, json={}), 201)
    assert ticket["expires_in"] == 30
    with browser.sockets.websocket_connect(f"{API}/ws/chat", params={"ticket": ticket["ticket"]}) as socket:
        acknowledgments = []
        for index, body in enumerate(messages):
            client_id = f"itest-message-{index}"
            socket.send_json({"type": "send", "room_id": room, "client_message_id": client_id, "body": body})
            ack = socket.receive_json()
            assert ack["type"] == "ack" and ack["client_message_id"] == client_id
            acknowledgments.append(ack)
    return acknowledgments


def test_signup_login_refresh_replay_and_logout(browser, register, service_db):
    request = browser.request
    member, other = register(), register()
    with service_db.connect() as db:
        assert db.scalar(text("""
            SELECT password_hash LIKE '$argon2id$%' AND last_login_at IS NOT NULL
            FROM public.users WHERE user_id = :uid
        """), {"uid": member.user_id})

    old = member.login["refresh_token"]
    rotated = checked(request("POST", f"{AUTH}/refresh", json={"refresh_token": old}), 200)
    assert rotated["user"]["user_id"] == str(member.user_id)
    fresh = rotated["refresh_token"]
    assert refresh_hash(old) != refresh_hash(fresh)
    checked(request("GET", FAVORITES, headers=auth_header(rotated)), 200)
    with service_db.connect() as db:
        rows = db.execute(text("""
            SELECT token_hash, revoked_at IS NOT NULL FROM public.refresh_tokens WHERE user_id = :uid
        """), {"uid": member.user_id}).all()
        assert dict(rows) == {refresh_hash(old): True, refresh_hash(fresh): False}

    checked(request("POST", f"{AUTH}/refresh", json={"refresh_token": old}), 401, "REFRESH_REUSED")
    with service_db.connect() as db:
        assert db.scalar(text("""
            SELECT count(*) FROM public.refresh_tokens WHERE user_id = :uid AND revoked_at IS NULL
        """), {"uid": member.user_id}) == 0
    checked(request("POST", f"{AUTH}/refresh", json={"refresh_token": fresh}), 401, "REFRESH_REUSED")
    current = checked(request("POST", f"{AUTH}/login", json=member.credentials), 200)
    logout = f"{AUTH}/logout"
    checked(request("POST", logout, headers=other.headers,
                    json={"refresh_token": current["refresh_token"]}), 401, "REFRESH_INVALID")
    checked(request("POST", logout, headers=auth_header(current),
                    json={"refresh_token": current["refresh_token"]}), 204)
    checked(request("GET", FAVORITES, headers=auth_header(current)), 401, "UNAUTHORIZED")
    checked(request("POST", f"{AUTH}/refresh", json={"refresh_token": current["refresh_token"]}),
            401, "REFRESH_REUSED")
    checked(request("GET", FAVORITES, headers=other.headers), 200)
    checked(request("POST", f"{AUTH}/refresh", json={"refresh_token": other.login["refresh_token"]}), 200)


def test_public_festival_catalog_and_private_favorites(browser, register, festivals):
    request = browser.request
    member, other = register(), register()
    ids, key = festivals
    public_id = ids["public"]
    catalog = f"{API}/festivals"
    page = checked(request("GET", catalog, params={"q": key}), 200)
    assert page["is_mock"] is False and page["total"] == 1
    assert [item["festival_id"] for item in page["items"]] == [public_id]
    details = checked(request("GET", f"{catalog}/{public_id}"), 200)
    assert details["festival_id"] == public_id and details["name"] == f"통합시험 {key}"
    for hidden in (ids["pending"], ids["event"]):
        checked(request("GET", f"{catalog}/{hidden}"), 404, "FESTIVAL_NOT_FOUND")
        checked(request("PUT", f"{FAVORITES}/{hidden}", headers=member.headers), 404, "FESTIVAL_NOT_FOUND")

    favorite = f"{FAVORITES}/{public_id}"
    saved = checked(request("PUT", favorite, headers=member.headers), 201)
    assert saved["festival_id"] == public_id
    assert checked(request("PUT", favorite, headers=member.headers), 200) == saved
    checked(request("DELETE", favorite, headers=other.headers), 204)
    assert checked(request("GET", FAVORITES, headers=other.headers), 200)["total"] == 0
    owned = checked(request("GET", FAVORITES, headers=member.headers), 200)
    assert owned["total"] == 1 and owned["items"][0]["festival_id"] == public_id
    query = "SELECT count(*) FROM public.favorites WHERE user_id = :owner AND festival_id = :id"
    assert rls_count(browser, member, query, owner=member.user_id, id=public_id) == 1
    assert rls_count(browser, other, query, owner=member.user_id, id=public_id) == 0
    checked(request("DELETE", favorite, headers=member.headers), 204)
    assert checked(request("GET", FAVORITES, headers=member.headers), 200)["items"] == []


def test_midterm_search_detail_return_and_result(browser, festivals, service_db):
    """공개 DB 축제의 동일 ID를 검색부터 귀가 결과까지 사용한다."""
    ids, key = festivals
    with service_db.begin() as db:
        db.execute(text("""
            UPDATE public.festivals
               SET venue_name = '광화문광장', latitude = 37.5759, longitude = 126.9768
             WHERE festival_id = :festival_id
        """), {"festival_id": ids["public"]})
    page = checked(browser.request("GET", f"{API}/festivals", params={"q": key}), 200)
    assert page["total"] == 1 and page["is_mock"] is False
    selected = page["items"][0]
    assert selected["festival_id"] == ids["public"]

    detail = checked(browser.request("GET", f"{API}/festivals/{selected['festival_id']}"), 200)
    assert detail["festival_id"] == selected["festival_id"]
    assert detail["lat"] is not None and detail["lng"] is not None

    submitted = browser.request("POST", f"{API}/routes/return", json={
        "request_id": f"midterm-{uuid4().hex}", "festival_id": detail["festival_id"],
        "destination": {"query": "서울역"},
    })
    assert submitted.status_code == 202
    assert submitted.headers["X-Mock"] == "true"  # 경로 공급원만 모의
    queued = submitted.json()
    token = queued["route_access_token"]
    assert token and queued["status_url"]

    states = []
    for _ in range(4):
        result = browser.request("GET", queued["status_url"], headers={"X-Route-Access-Token": token})
        assert result.status_code == 200
        body = result.json()
        states.append(body["route_status"])
        if body["route_status"] == "ready":
            assert body["festival_id"] == detail["festival_id"]
            assert body["origin"]["lat"] == detail["lat"]
            assert body["origin"]["lng"] == detail["lng"]
            assert body["route_candidates"]
            break
    else:
        pytest.fail(f"발표 동선의 경로 결과가 준비되지 않음: {states}")


def test_friends_direct_chat_cursor_concurrent_create_and_block(browser, register, service_db):
    request = browser.request
    sender, recipient, outsider = register(), register(), register()
    req_id = friend_request(request, sender, recipient)
    inbox = f"{API}/me/friend-requests"
    assert [item["request_id"] for item in checked(request("GET", inbox, headers=recipient.headers), 200)["items"]] == [
        req_id,
    ]
    checked(request("POST", f"{FRIEND_REQUESTS}/{req_id}/accept", headers=outsider.headers), 404, "NOT_FOUND")
    assert rls_count(browser, outsider, "SELECT count(*) FROM public.friend_requests WHERE request_id = :id",
                     id=req_id) == 0
    accept_friend(request, recipient, req_id)
    friends = checked(request("GET", f"{API}/me/friends", headers=sender.headers), 200)
    assert [item["user_id"] for item in friends["items"]] == [str(recipient.user_id)]

    async def create_from_both_ends():
        return await asyncio.gather(
            browser.http.post(ROOMS, headers=sender.headers, json=direct_body(recipient)),
            browser.http.post(ROOMS, headers=recipient.headers, json=direct_body(sender)),
        )

    responses = sorted(browser.run(create_from_both_ends), key=lambda response: response.status_code)
    existing, created = (checked(response, status) for response, status in zip(responses, (200, 201), strict=True))
    room = created["room_id"]
    assert existing["room_id"] == room
    first, second = send_messages(browser, sender, room, "첫 번째 메시지", "두 번째 메시지")
    assert (first["seq"], second["seq"]) == (1, 2)
    history = f"{ROOMS}/{room}/messages"
    from_cursor = checked(request("GET", history, headers=recipient.headers, params={"after_seq": first["seq"]}), 200)
    assert [(item["seq"], item["body"]) for item in from_cursor["items"]] == [(2, "두 번째 메시지")]
    assert from_cursor["has_more"] is False
    assert checked(request("GET", history, headers=recipient.headers,
                           params={"after_seq": second["seq"]}), 200)["items"] == []
    checked(request("GET", history, headers=outsider.headers), 403, "FORBIDDEN")
    assert rls_count(browser, outsider, "SELECT count(*) FROM public.chat_messages WHERE room_id = :id", id=room) == 0

    def room_state():
        with service_db.connect() as db:
            return tuple(db.execute(text("""
                SELECT status, closed_by_block, last_seq FROM public.chat_rooms WHERE room_id = :room
            """), {"room": room}).one())

    assert room_state() == ("active", False, 2)
    block = f"{API}/me/blocks/{sender.user_id}"
    assert checked(request("PUT", block, headers=recipient.headers), 200) == {"blocked": True}
    assert room_state() == ("closed", True, 2)
    checked(request("GET", history, headers=sender.headers), 403, "FORBIDDEN")
    checked(request("DELETE", block, headers=recipient.headers), 204)
    assert room_state() == ("closed", True, 2)
    checked(request("GET", history, headers=recipient.headers), 403, "FORBIDDEN")
    assert checked(request("GET", f"{API}/me/friends", headers=sender.headers), 200)["items"] == []


def test_companion_approval_controls_meeting_place_api_and_rls(browser, register, festivals):
    request = browser.request
    author, approved, pending = register(), register(), register()
    festival_id = festivals[0]["public"]
    created = checked(request("POST", POSTS, headers=author.headers, json={
        "festival_id": festival_id, "meet_at": (datetime.now(KST) + timedelta(days=1)).isoformat(),
        "capacity": 1, "memo": "축제 같이 둘러보기",
    }), 201)
    post_id = created["post_id"]
    post = f"{POSTS}/{post_id}"
    applications = f"{post}/applications"
    meeting = f"{post}/meeting-place"
    place = {"name": "정문", "address": "합성 시험 광장"}
    checked(request("PUT", meeting, headers=author.headers, json=place), 200)
    applicant_id = checked(request("POST", applications, headers=approved.headers,
                                   json={"message": "동행 신청합니다"}), 201)["application_id"]
    checked(request("POST", applications, headers=pending.headers, json={}), 201)
    checked(request("GET", meeting, headers=approved.headers), 403, "FORBIDDEN")
    decision = f"{API}/companion-applications/{applicant_id}/approve"
    checked(request("POST", decision, headers=pending.headers), 403, "FORBIDDEN")
    assert checked(request("POST", decision, headers=author.headers), 200) == {
        "application_id": applicant_id, "status": "approved", "post_status": "full",
    }

    for member in (author, approved, pending):
        visible = member is not pending
        response = request("GET", meeting, headers=member.headers)
        if visible:
            body = checked(response, 200)
            assert {key: body[key] for key in place} == place
        else:
            checked(response, 403, "FORBIDDEN")
        assert rls_count(browser, member, "SELECT count(*) FROM public.meeting_places WHERE post_id = :id",
                         id=post_id) == int(visible)
    public = checked(request("GET", post), 200)
    assert "meeting_place" not in public and place["address"] not in str(public)


def test_message_report_records_operator_access(browser, register, service_db):
    request = browser.request
    reporter, sender, operator = register(), register(), register(operator=True)
    accept_friend(request, sender, friend_request(request, reporter, sender))
    room = checked(request("POST", ROOMS, headers=reporter.headers, json=direct_body(sender)), 201)["room_id"]
    body = "신고 대상 합성 메시지"
    message_id = send_messages(browser, sender, room, body)[0]["message_id"]
    report = {"target_type": "chat_message", "target_id": str(message_id), "reason": "spam"}
    checked(request("POST", f"{API}/reports", headers=operator.headers, json=report), 404, "NOT_FOUND")
    report_id = checked(request("POST", f"{API}/reports", headers=reporter.headers, json=report), 201)["report_id"]
    params = {"report_id": report_id}
    checked(request("GET", ADMIN_REPORTS, headers=sender.headers, params=params), 403, "FORBIDDEN")
    inbox = checked(request("GET", ADMIN_REPORTS, headers=operator.headers, params={"status": "received"}), 200)
    assert any(item["report_id"] == report_id for item in inbox["items"])
    with service_db.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM public.chat_admin_access WHERE report_id = :report_id"), params) == 0
    detail = checked(request("GET", ADMIN_REPORTS, headers=operator.headers, params=params), 200)
    assert detail["report"]["status"] == "reviewing"
    assert detail["room"]["room_id"] == room and detail["message"]["body"] == body
    assert detail["message"]["message_id"] == message_id
    with service_db.connect() as db:
        row = db.execute(text("""
            SELECT access_id, admin_id, room_id, reason FROM public.chat_admin_access WHERE report_id = :report_id
        """), params).one()
        assert tuple(row) == (detail["access_id"], operator.user_id, room, "spam")


def test_assistant_submission_worker_once_and_private_result(browser, register, service_db):
    request = browser.request
    owner, other = register(), register()
    message = "축제는 어디에서 열리나요?"
    queued = checked(request("POST", f"{API}/assistant/query", headers=owner.headers, json={
        "request_id": f"itest-{uuid4().hex}", "message": message,
    }), 202)
    assert queued["run_status"] == "queued"
    url = queued["status_url"]
    assert checked(request("GET", url, headers=owner.headers), 200)["run_status"] == "queued"
    checked(request("GET", url, headers=other.headers), 403, "FORBIDDEN")
    queue = PostgresAssistantQueue()
    answer = "합성 답변입니다."
    processed = []

    def fixture_answer(claim):
        job = queue.load(claim)
        processed.append((claim.run_id, claim.attempt, job.query.message if job else None))
        queue.step(claim, "festival")
        return AgentResult(answer=answer, is_mock=True), False

    assert work_once(queue, fixture_answer)
    assert processed == [(queued["run_id"], 1, message)]
    result = checked(request("GET", url, headers=owner.headers), 200)
    assert (result["run_status"], result["answer"], result["is_mock"]) == ("succeeded", answer, True)
    checked(request("GET", url, headers=other.headers), 403, "FORBIDDEN")
    query = "SELECT count(*) FROM public.assistant_runs WHERE run_id = :id"
    assert rls_count(browser, owner, query, id=queued["run_id"]) == 1
    assert rls_count(browser, other, query, id=queued["run_id"]) == 0
    with service_db.connect() as db:
        row = db.execute(text("""
            SELECT run_status, attempt, answer FROM public.assistant_runs WHERE run_id = :id
        """), {"id": queued["run_id"]}).one()
        assert tuple(row) == ("succeeded", 1, answer)


def test_scheduler_once_removes_expired_rows_and_keeps_recent(browser, register, service_db, monkeypatch):
    request = browser.request
    sender, old_recipient, recent_recipient = register(), register(), register()
    old = friend_request(request, sender, old_recipient)
    recent = friend_request(request, sender, recent_recipient)
    for rec, request_id in ((old_recipient, old), (recent_recipient, recent)):
        checked(request("POST", f"{FRIEND_REQUESTS}/{request_id}/reject", headers=rec.headers), 200)
    with service_db.begin() as db:
        db.execute(text("""
            UPDATE public.friend_requests
            SET created_at = now() - interval '32 days', responded_at = now() - interval '31 days'
            WHERE request_id = :id
        """), {"id": old})
        db.execute(text("""
            UPDATE public.notifications SET created_at = now() - interval '91 days' WHERE ref_id = :id
        """), {"id": old})
        assert db.scalar(text("SELECT count(*) FROM public.notifications WHERE ref_id = :id"), {"id": old}) == 1

    calls = []

    def collect_fixture(since, *, locked_engine):
        calls.append((since, locked_engine))
        return JobResult("fixture", "succeeded", 0, 0, 0, 0)

    monkeypatch.setattr(scheduler.collect, "collect_to_db", collect_fixture)
    now = datetime.now(KST).replace(hour=7, minute=0, second=0, microsecond=0)
    assert scheduler.run_due(now) == 0
    assert calls == [(now.date().replace(month=1, day=1), service_db)]
    ids = {"old": old, "recent": recent}
    with service_db.connect() as db:
        assert db.execute(text("""
            SELECT request_id FROM public.friend_requests WHERE request_id IN (:old, :recent)
        """), ids).scalars().all() == [recent]
        assert db.execute(text("""
            SELECT ref_id FROM public.notifications WHERE ref_id IN (:old, :recent)
        """), ids).scalars().all() == [recent]
        assert db.scalar(text("""
            SELECT last_success_slot FROM public.scheduled_job_runs WHERE job_name = 'retention'
        """)) == now.replace(hour=6)
