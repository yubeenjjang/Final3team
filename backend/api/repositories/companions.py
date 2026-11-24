from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from ulid import ULID

from api.auth.tokens import unauthorized
from api.repositories.friends import is_blocked, lock_users
from api.repositories.notifications import add as add_notifications
from api.schemas import companions as schema
from api.services import companion_rules as rules
from api.services.friends import blocked
from api.services.companion_chat import ChatRooms, append_system_message

_PUBLIC_FESTIVAL = """
    SELECT start_date, end_date FROM public.festivals
    WHERE festival_id = :festival_id AND category = 'festival'
      AND source_class_level2 = 'EV01' AND review_status = 'approved' AND published_at IS NOT NULL
"""
_POST_FIELDS = """
    p.post_id, public.app_public_display_name(p.author_id) AS author_display_name,
    p.meet_at, p.capacity, p.approved_count, p.age_pref, p.gender_pref,
    CASE WHEN p.ended_at IS NULL OR p.ended_at > statement_timestamp() - interval '72 hours'
         THEN p.memo END AS memo,
    CASE WHEN p.status IN ('open', 'full') AND p.meet_at <= :auto_before
         THEN 'ended' ELSE p.status END AS status
"""


class CompanionReads:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_posts(self, festival_id: str, status: schema.PostStatus, page: int) -> schema.PostList:
        params = {"festival_id": festival_id}
        if (await self.db.execute(text(_PUBLIC_FESTIVAL), params)).first() is None:
            raise rules.festival_not_found()
        rows = (await self.db.execute(text(f"""
            SELECT * FROM (
                SELECT {_POST_FIELDS}
                FROM public.companion_posts p WHERE p.festival_id = :festival_id
            ) visible
            WHERE status = :status ORDER BY meet_at, post_id LIMIT :size OFFSET :offset
        """), {**params, "status": status, "size": rules.PAGE_SIZE,
               "offset": min((page - 1) * rules.PAGE_SIZE, 2**63 - 1),
               "auto_before": rules.now_utc() - rules.auto_end_after()})).mappings()
        return schema.PostList(items=[schema.PostItem.model_validate(row) for row in rows])

    async def get_post(self, post_id: str) -> schema.PostDetail:
        row = (await self.db.execute(text(f"""
            SELECT {_POST_FIELDS}, (
                SELECT a.status FROM public.companion_applications a
                WHERE a.post_id = p.post_id AND a.applicant_id = public.app_current_user()
                ORDER BY (a.status <> 'cancelled') DESC, a.created_at DESC, a.application_id DESC
                LIMIT 1
            ) AS my_application_status
            FROM public.companion_posts p WHERE p.post_id = :post_id
        """), {"post_id": post_id, "auto_before": rules.now_utc() - rules.auto_end_after()})).mappings().one_or_none()
        if row is None:
            raise rules.not_found()
        return schema.PostDetail.model_validate(row)

    async def list_applications(
        self, post_id: str, status: schema.VisibleApplicationStatus | None,
    ) -> schema.ApplicationList:
        params = {"post_id": post_id}
        owns_post = await self.db.scalar(text("""
            SELECT author_id = public.app_current_user()
            FROM public.companion_posts WHERE post_id = :post_id
        """), params)
        if owns_post is None:
            raise rules.not_found()
        if not owns_post:
            raise rules.forbidden()
        rows = (await self.db.execute(text("""
            SELECT a.application_id, profile.display_name AS applicant_display_name,
                   :year - profile.birth_year AS applicant_age, profile.gender AS applicant_gender,
                   CASE WHEN p.ended_at IS NULL OR p.ended_at > statement_timestamp() - interval '72 hours'
                        THEN a.message END AS message,
                   a.status, a.created_at
            FROM public.companion_applications a JOIN public.companion_posts p USING (post_id)
            LEFT JOIN LATERAL public.app_applicant_profile(a.application_id) profile ON true
            WHERE a.post_id = :post_id AND a.status IN ('pending', 'approved')
              AND (CAST(:status AS text) IS NULL OR a.status = :status)
            ORDER BY a.created_at, a.application_id
        """), {**params, "status": status, "year": rules.now_utc().astimezone(rules.KST).year})).mappings()
        return schema.ApplicationList(items=[schema.ApplicationItem.model_validate(row) for row in rows])

    async def get_meeting_place(self, post_id: str) -> schema.MeetingPlaceDetail | schema.MeetingPlaceUndecided:
        params = {"post_id": post_id}
        row = (await self.db.execute(text("""
            SELECT public.app_room_joined_at(room_id) IS NOT NULL AS joined
            FROM public.companion_posts WHERE post_id = :post_id
        """), params)).one_or_none()
        if row is None:
            raise rules.not_found()
        if not row.joined:
            raise rules.forbidden()
        place = (await self.db.execute(text("""
            SELECT name, address, lat, lng, guide, updated_at
            FROM public.meeting_places WHERE post_id = :post_id
        """), params)).mappings().one_or_none()
        return schema.MeetingPlaceDetail.model_validate(place) if place else schema.MeetingPlaceUndecided()


class CompanionWrites:
    def __init__(self, db: Session, actor_id: UUID):
        self.db = db
        self.actor_id = actor_id

    def _lock_actor(self) -> None:
        # Serialize the actor with A80, and allow other transactions' FK checks.
        active = self.db.scalar(text("""
            SELECT status = 'active' FROM public.users WHERE user_id = :actor FOR SHARE
        """), {"actor": self.actor_id})
        if not active:
            raise unauthorized()

    def locked_post(self, post_id: str) -> Row:
        self._lock_actor()
        post = self.db.execute(text("""
            SELECT post_id, festival_id, author_id, room_id, meet_at, capacity, approved_count,
                   status, recruitment_closed_at
            FROM public.companion_posts
            WHERE post_id = :post_id AND (hidden_at IS NULL OR author_id = :actor)
            FOR UPDATE
        """), {"post_id": post_id, "actor": self.actor_id}).one_or_none()
        if post is None:
            raise rules.not_found()
        return post

    def own_post(self, post_id: str) -> Row:
        post = self.locked_post(post_id)
        if post.author_id != self.actor_id:
            raise rules.forbidden()
        return post

    def validate_meeting(self, festival_id: str, meet_at: datetime, now: datetime) -> None:
        festival = self.db.execute(text(_PUBLIC_FESTIVAL), {"festival_id": festival_id}).one_or_none()
        if festival is None:
            raise rules.festival_not_found()
        rules.validate_meeting(meet_at, festival.start_date, festival.end_date, now)

    def create_post(self, request: schema.PostCreate) -> schema.PostCreated:
        self._lock_actor()
        self.validate_meeting(request.festival_id, request.meet_at, rules.now_utc())
        post_id = "cpo_" + str(ULID())
        room_id = ChatRooms.create_companion_room(self.db, self.actor_id)
        ChatRooms.add_member(self.db, room_id, self.actor_id, role="owner")
        self.db.execute(text("""
            INSERT INTO public.companion_posts
              (post_id, festival_id, author_id, room_id, meet_at, capacity, age_pref, gender_pref, memo)
            VALUES (:post_id, :festival_id, :author, :room_id, :meet_at, :capacity, :age_pref, :gender_pref, :memo)
        """), {**request.model_dump(), "post_id": post_id, "author": self.actor_id, "room_id": room_id})
        return schema.PostCreated(post_id=post_id, room_id=room_id)

    def update_post(self, post_id: str, request: schema.PostUpdate) -> schema.PostChanged:
        post = self.own_post(post_id)
        now = rules.now_utc()
        rules.require_active(post.status, post.meet_at, now)
        changes = request.model_dump(exclude_unset=True)
        if request.meet_at is not None:
            self.validate_meeting(post.festival_id, request.meet_at, now)
        capacity = request.capacity if request.capacity is not None else post.capacity
        status = rules.edited_status(capacity, post.approved_count, post.recruitment_closed_at is not None)
        # The column names come from PostUpdate's declared fields.
        assignments = ", ".join(f"{column} = :{column}" for column in changes)
        self.db.execute(text(f"""
            UPDATE public.companion_posts SET {assignments}, status = :status WHERE post_id = :post_id
        """), {**changes, "status": status, "post_id": post_id})
        return schema.PostChanged(post_id=post_id, status=status)

    def create_application(self, post_id: str, request: schema.ApplicationCreate) -> schema.ApplicationCreated:
        author_id = self.db.scalar(text("""
            SELECT author_id FROM public.companion_posts WHERE post_id = :post_id
        """), {"post_id": post_id})
        if author_id is None:
            raise rules.not_found()
        # Use the same user lock order as A49/A50, before taking the post lock.
        lock_users(self.db, self.actor_id, author_id)
        post = self.locked_post(post_id)
        rules.check_application(post.author_id, self.actor_id, post.status)
        rules.require_active(post.status, post.meet_at, rules.now_utc())
        if is_blocked(self.db, self.actor_id, post.author_id):
            raise blocked()
        application_id = self.db.scalar(text("""
            INSERT INTO public.companion_applications (application_id, post_id, applicant_id, message)
            VALUES (:application_id, :post_id, :actor, :message)
            ON CONFLICT (post_id, applicant_id) WHERE status IN ('pending', 'approved', 'rejected')
            DO NOTHING RETURNING application_id
        """), {"application_id": "cap_" + str(ULID()), "post_id": post_id,
               "actor": self.actor_id, "message": request.message})
        if application_id is None:
            raise rules.application_exists()
        add_notifications(self.db, [post.author_id], "companion_applied", "companion_application", application_id)
        return schema.ApplicationCreated(application_id=application_id)

    def decide_application(self, application_id: str, action: schema.ApplicationAction) -> schema.ApplicationChanged:
        params = {"application_id": application_id}
        candidate = self.db.execute(text("""
            SELECT a.post_id, a.applicant_id, p.author_id
            FROM public.companion_applications a JOIN public.companion_posts p USING (post_id)
            WHERE a.application_id = :application_id
        """), params).one_or_none()
        if candidate is None:
            raise rules.not_found()
        if action == "approve" and candidate.author_id == self.actor_id:
            lock_users(self.db, self.actor_id, candidate.applicant_id)

        # Capacity edits and application changes take the post lock before any application lock.
        post = self.locked_post(candidate.post_id)
        application = self.db.execute(text("""
            SELECT applicant_id, status FROM public.companion_applications
            WHERE application_id = :application_id FOR UPDATE
        """), params).one()
        authorized_actor = application.applicant_id if action == "cancel" else post.author_id
        if authorized_actor != self.actor_id:
            raise rules.forbidden()

        rules.require_pending(application.status)
        post_status = post.status
        status = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[action]
        if action == "approve":
            if is_blocked(self.db, self.actor_id, application.applicant_id):
                raise blocked()
            rules.require_active(post.status, post.meet_at, rules.now_utc())
            rules.require_approval_slot(post.status, post.approved_count, post.capacity)
            post_status = self.db.scalar(text("""
                UPDATE public.companion_posts
                SET approved_count = approved_count + 1,
                    status = CASE WHEN approved_count + 1 = capacity THEN 'full' ELSE 'open' END
                WHERE post_id = :post_id RETURNING status
            """), {"post_id": post.post_id})
        self.db.execute(text("""
            UPDATE public.companion_applications SET status = :status, decided_at = clock_timestamp()
            WHERE application_id = :application_id
        """), {**params, "status": status})
        if action == "approve":
            ChatRooms.add_member(self.db, post.room_id, application.applicant_id)
            append_system_message(self.db, post.room_id, "새 참여자가 동행에 합류했어요.")
        if action != "cancel":
            add_notifications(self.db, [application.applicant_id], f"companion_{status}",
                              "companion_application", application_id)
        return schema.ApplicationChanged(application_id=application_id, status=status, post_status=post_status)

    def set_meeting_place(self, post_id: str, request: schema.MeetingPlace) -> schema.MeetingPlaceUpdated:
        post = self.own_post(post_id)
        rules.require_active(post.status, post.meet_at, rules.now_utc())
        updated_at = self.db.scalar(text("""
            INSERT INTO public.meeting_places (post_id, name, address, lat, lng, guide, updated_by)
            VALUES (:post_id, :name, :address, :lat, :lng, :guide, :actor)
            ON CONFLICT (post_id) DO UPDATE SET name = EXCLUDED.name, address = EXCLUDED.address,
                lat = EXCLUDED.lat, lng = EXCLUDED.lng, guide = EXCLUDED.guide,
                updated_by = EXCLUDED.updated_by, updated_at = clock_timestamp()
            WHERE (meeting_places.name, meeting_places.address, meeting_places.lat,
                   meeting_places.lng, meeting_places.guide) IS DISTINCT FROM
                  (EXCLUDED.name, EXCLUDED.address, EXCLUDED.lat, EXCLUDED.lng, EXCLUDED.guide)
            RETURNING updated_at
        """), {**request.model_dump(), "post_id": post_id, "actor": self.actor_id})
        if updated_at is None:
            updated_at = self.db.scalar(text("""
                SELECT updated_at FROM public.meeting_places WHERE post_id = :post_id
            """), {"post_id": post_id})
        else:
            append_system_message(self.db, post.room_id, "만남 장소가 변경됐어요.")
            _notify_members(self.db, post, "meeting_place_changed")
        return schema.MeetingPlaceUpdated(post_id=post_id, updated_at=updated_at)

    def change_post(self, post_id: str, action: schema.PostAction) -> schema.PostChanged:
        post = self.own_post(post_id)
        now = rules.now_utc()
        status = rules.post_action_status(action, post.status, post.meet_at, now)
        if action == "close":
            self.db.execute(text("""
                UPDATE public.companion_posts
                SET status = 'full', recruitment_closed_at = COALESCE(recruitment_closed_at, :now)
                WHERE post_id = :post_id
            """), {"post_id": post_id, "now": now})
        else:
            _finish_post(self.db, post, status, now)
        return schema.PostChanged(post_id=post_id, status=status)


def _notify_members(db: Session, post: Row, event: str) -> None:
    db.execute(text("""
        INSERT INTO public.notifications (user_id, type, ref_type, ref_id)
        SELECT m.user_id, :event, 'companion_post', :post_id FROM public.chat_members m
        JOIN public.users u USING (user_id)
        WHERE m.room_id = :room_id AND m.user_id <> :author_id AND m.status = 'joined' AND u.status = 'active'
    """), {"event": event, "post_id": post.post_id, "room_id": post.room_id, "author_id": post.author_id})


def _finish_post(db: Session, post: Row, status: schema.PostStatus, ended_at: datetime) -> None:
    params = {"post_id": post.post_id, "room_id": post.room_id, "status": status, "ended_at": ended_at}
    db.execute(text("""
        UPDATE public.companion_posts SET status = :status, ended_at = :ended_at WHERE post_id = :post_id
    """), params)
    db.execute(text("""
        UPDATE public.chat_rooms
        SET status = CASE WHEN status = 'active' THEN 'read_only' ELSE status END,
            read_only_at = :ended_at WHERE room_id = :room_id
    """), params)
    _notify_members(db, post, f"companion_{status}")


def maintain_companions(db: Session, now: datetime) -> dict[str, int]:
    auto_end = rules.auto_end_after()
    due = db.execute(text("""
        SELECT post_id, room_id, author_id, meet_at FROM public.companion_posts
        WHERE status IN ('open', 'full') AND meet_at <= :cutoff
        ORDER BY post_id FOR UPDATE SKIP LOCKED
    """), {"cutoff": now - auto_end}).all()
    for post in due:
        _finish_post(db, post, "ended", post.meet_at + auto_end)

    params = {"cutoff": now - rules.RETENTION, "now": now}
    expired = "p.ended_at <= :cutoff AND p.status IN ('ended', 'cancelled')"
    cleared_memos = db.execute(text(f"""
        UPDATE public.companion_posts p SET memo = NULL WHERE {expired} AND p.memo IS NOT NULL
    """), params).rowcount
    cleared_places = db.execute(text(f"""
        DELETE FROM public.meeting_places mp USING public.companion_posts p
        WHERE mp.post_id = p.post_id AND {expired}
    """), params).rowcount
    cleared_applications = db.execute(text(f"""
        UPDATE public.companion_applications a SET message = NULL FROM public.companion_posts p
        WHERE a.post_id = p.post_id AND {expired} AND a.message IS NOT NULL
    """), params).rowcount
    cleared_chat = db.execute(text(f"""
        UPDATE public.chat_messages m SET body = NULL, deleted_at = COALESCE(deleted_at, :now)
        FROM public.companion_posts p WHERE m.room_id = p.room_id AND {expired} AND m.body IS NOT NULL
    """), params).rowcount
    return {"ended": len(due), "memos": cleared_memos, "places": cleared_places,
            "applications": cleared_applications, "messages": cleared_chat}
