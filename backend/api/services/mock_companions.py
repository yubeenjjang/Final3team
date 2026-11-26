from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from uuid import UUID

from ulid import ULID

from api.mocks import store
from api.schemas import companions as schema
from api.services import companion_rules as rules
from api.services import mock_chat, mock_friends
from api.services.friends import blocked


@dataclass
class Post:
    post_id: str
    festival_id: str
    author_id: str
    room_id: str
    meet_at: datetime
    capacity: int
    age_pref: schema.AgePreference | None
    gender_pref: schema.GenderPreference
    memo: str | None
    status: schema.PostStatus = "open"
    approved_count: int = 0
    recruitment_closed: bool = False
    ended_at: datetime | None = None
    members: set[str] = field(default_factory=set)
    place: schema.MeetingPlaceDetail | None = None
    hidden: bool = False


@dataclass
class Application:
    application_id: str
    applicant_id: str
    post_id: str
    message: str | None
    created_at: datetime
    status: schema.ApplicationStatus = "pending"


class MemoryCompanions:
    """Redis 연동 전 한 프로세스에서 사용하는 동행 저장소."""

    def __init__(self):
        self.lock = Lock()
        self.posts: dict[str, Post] = {}
        self.applications: dict[str, Application] = {}

    def maintenance(self, now: datetime) -> None:
        auto_end = rules.auto_end_after()
        expired = set()
        for post in self.posts.values():
            if post.status in {"open", "full"} and post.meet_at + auto_end <= now:
                post.status = "ended"
                post.ended_at = post.meet_at + auto_end
                mock_chat.mock_rooms.finish_companion_room(post.room_id, post.ended_at)
            if post.ended_at is not None and post.ended_at + rules.RETENTION <= now:
                post.memo = None
                post.place = None
                expired.add(post.post_id)
        for application in self.applications.values():
            if application.post_id in expired:
                application.message = None

    def get_post(self, post_id: str) -> Post:
        post = self.posts.get(post_id)
        if post is None:
            raise rules.not_found()
        return post

    def validate_meeting(self, festival_id: str, meet_at: datetime, now: datetime) -> None:
        festival = store.get_public_mock_festival(festival_id)
        if festival is None:
            raise rules.festival_not_found()
        rules.validate_meeting(meet_at, festival.start_date, festival.end_date, now)

    def user(self, user_id: str) -> store.MockUser | None:
        with store.auth_lock:
            return next((user for user in store.users_by_email.values() if user.user_id == user_id), None)

    def item(self, post: Post) -> schema.PostItem:
        author = self.user(post.author_id)
        return schema.PostItem(
            post_id=post.post_id, author_display_name=author.display_name if author else None,
            meet_at=post.meet_at, capacity=post.capacity, approved_count=post.approved_count,
            age_pref=post.age_pref, gender_pref=post.gender_pref, memo=post.memo, status=post.status,
        )


class MockCompanions:
    def __init__(self, memory: MemoryCompanions, actor_id: str | None):
        self.memory = memory
        self.actor_id = actor_id

    def list_posts(self, festival_id: str, status: schema.PostStatus, page: int) -> schema.PostList:
        if store.get_public_mock_festival(festival_id) is None:
            raise rules.festival_not_found()
        rows = [
            post for post in self.memory.posts.values()
            if post.festival_id == festival_id and post.status == status
            and (not post.hidden or post.author_id == self.actor_id)
        ]
        rows.sort(key=lambda post: (post.meet_at, post.post_id))
        offset = (page - 1) * rules.PAGE_SIZE
        return schema.PostList(items=[self.memory.item(post) for post in rows[offset:offset + rules.PAGE_SIZE]])

    def get_post(self, post_id: str) -> schema.PostDetail:
        post = self.memory.get_post(post_id)
        if post.hidden and post.author_id != self.actor_id:
            raise rules.not_found()
        latest = next((
            row for row in reversed(self.memory.applications.values())
            if row.post_id == post_id and row.applicant_id == self.actor_id
        ), None)
        return schema.PostDetail(
            **self.memory.item(post).model_dump(), my_application_status=latest.status if latest else None,
        )

    def own_post(self, post_id: str) -> Post:
        post = self.memory.get_post(post_id)
        if post.author_id != self.actor_id:
            raise rules.forbidden()
        return post

    def create_post(self, request: schema.PostCreate) -> schema.PostCreated:
        assert self.actor_id is not None
        self.memory.validate_meeting(request.festival_id, request.meet_at, rules.now_utc())
        post_id = "cpo_" + str(ULID())
        room_id = mock_chat.mock_rooms.create_companion_room(post_id, UUID(self.actor_id))
        self.memory.posts[post_id] = Post(
            **request.model_dump(), post_id=post_id, room_id=room_id, author_id=self.actor_id,
            members={self.actor_id},
        )
        return schema.PostCreated(post_id=post_id, room_id=room_id)

    def update_post(self, post_id: str, request: schema.PostUpdate) -> schema.PostChanged:
        post = self.own_post(post_id)
        now = rules.now_utc()
        rules.require_active(post.status, post.meet_at, now)
        if request.meet_at is not None:
            self.memory.validate_meeting(post.festival_id, request.meet_at, now)
        capacity = request.capacity if request.capacity is not None else post.capacity
        status = rules.edited_status(capacity, post.approved_count, post.recruitment_closed)
        for column, value in request.model_dump(exclude_unset=True).items():
            setattr(post, column, value)
        post.status = status
        return schema.PostChanged(post_id=post_id, status=status)

    def create_application(self, post_id: str, request: schema.ApplicationCreate) -> schema.ApplicationCreated:
        assert self.actor_id is not None
        post = self.memory.get_post(post_id)
        if post.hidden and post.author_id != self.actor_id:
            raise rules.not_found()
        rules.check_application(post.author_id, self.actor_id, post.status)
        # Mock friend changes and these writes share the same lock.
        with store.auth_lock:
            if mock_friends.store.is_blocked(UUID(self.actor_id), UUID(post.author_id)):
                raise blocked()
            if any(
                row.post_id == post_id and row.applicant_id == self.actor_id and row.status != "cancelled"
                for row in self.memory.applications.values()
            ):
                raise rules.application_exists()
            application_id = "cap_" + str(ULID())
            self.memory.applications[application_id] = Application(
                application_id, self.actor_id, post_id, request.message, rules.now_utc(),
            )
            mock_chat.mock_rooms.notify(UUID(post.author_id), "companion_applied", "companion_application", application_id)
            return schema.ApplicationCreated(application_id=application_id)

    def list_applications(
        self, post_id: str, status: schema.VisibleApplicationStatus | None,
    ) -> schema.ApplicationList:
        self.own_post(post_id)
        year = rules.now_utc().astimezone(rules.KST).year
        items = []
        for row in self.memory.applications.values():
            if row.post_id != post_id or row.status not in {"pending", "approved"} or status not in {None, row.status}:
                continue
            user = self.memory.user(row.applicant_id)
            items.append(schema.ApplicationItem(
                application_id=row.application_id,
                applicant_display_name=user.display_name if user else None,
                applicant_age=year - user.birth_year if user else None,
                applicant_gender=user.gender if user else None,
                message=row.message, status=row.status, created_at=row.created_at,
            ))
        return schema.ApplicationList(items=items)

    def decide_application(self, application_id: str, action: schema.ApplicationAction) -> schema.ApplicationChanged:
        row = self.memory.applications.get(application_id)
        if row is None:
            raise rules.not_found()
        post = self.memory.get_post(row.post_id)
        actor = row.applicant_id if action == "cancel" else post.author_id
        if actor != self.actor_id:
            raise rules.forbidden()
        rules.require_pending(row.status)
        status = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[action]
        with store.auth_lock:
            if action == "approve":
                if mock_friends.store.is_blocked(UUID(post.author_id), UUID(row.applicant_id)):
                    raise blocked()
                rules.require_active(post.status, post.meet_at, rules.now_utc())
                rules.require_approval_slot(post.status, post.approved_count, post.capacity)
                mock_chat.mock_rooms.add_member(post.room_id, UUID(row.applicant_id))
                post.approved_count += 1
                post.status = rules.edited_status(post.capacity, post.approved_count, post.recruitment_closed)
                post.members.add(row.applicant_id)
            row.status = status
            if action != "cancel":
                mock_chat.mock_rooms.notify(UUID(row.applicant_id), f"companion_{status}",
                                            "companion_application", application_id)
            return schema.ApplicationChanged(application_id=application_id, status=status, post_status=post.status)

    def set_meeting_place(self, post_id: str, request: schema.MeetingPlace) -> schema.MeetingPlaceUpdated:
        post = self.own_post(post_id)
        now = rules.now_utc()
        rules.require_active(post.status, post.meet_at, now)
        if post.place is None or post.place.model_dump(exclude={"updated_at"}) != request.model_dump():
            post.place = schema.MeetingPlaceDetail(**request.model_dump(), updated_at=now)
        return schema.MeetingPlaceUpdated(post_id=post_id, updated_at=post.place.updated_at)

    def get_meeting_place(self, post_id: str) -> schema.MeetingPlaceDetail | schema.MeetingPlaceUndecided:
        post = self.memory.get_post(post_id)
        if self.actor_id not in post.members:
            raise rules.forbidden()
        return post.place or schema.MeetingPlaceUndecided()

    def change_post(self, post_id: str, action: schema.PostAction) -> schema.PostChanged:
        post = self.own_post(post_id)
        now = rules.now_utc()
        post.status = rules.post_action_status(action, post.status, post.meet_at, now)
        if action == "close":
            post.recruitment_closed = True
        else:
            post.ended_at = now
            mock_chat.mock_rooms.finish_companion_room(post.room_id, now)
        return schema.PostChanged(post_id=post_id, status=post.status)
