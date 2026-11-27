"""동행 모집, 신청, 만남 장소 API."""
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Concatenate, ParamSpec, TypeVar
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from api.auth.tokens import unauthorized, uses_auth_db
from api.deps import AuthenticatedSession, Authorization, CurrentUser, get_current_user
from api.mocks.store import auth_lock
from api.repositories.companions import CompanionReads, CompanionWrites
from api.schemas import companions as schema
from api.services import companion_rules as rules
from api.services.mock_auth import authenticated_access
from api.services.mock_companions import MemoryCompanions, MockCompanions
from shared.db.session import service_db_session, user_db_session

router = APIRouter(tags=["companions"])
FestivalId = Annotated[str, Path(pattern=schema.FESTIVAL_ID_PATTERN)]
PostId = Annotated[str, Path(pattern=schema.POST_ID_PATTERN)]
ApplicationId = Annotated[str, Path(pattern=schema.APPLICATION_ID_PATTERN)]


R = TypeVar("R")
P = ParamSpec("P")
memory = MemoryCompanions()


@dataclass
class CompanionSession:
    user_id: UUID | str | None
    db: AsyncSession | None = None

    async def read(
        self,
        db_method: Callable[Concatenate[CompanionReads, P], Awaitable[R]],
        mock_method: Callable[Concatenate[MockCompanions, P], R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        if self.db is not None:
            return await db_method(CompanionReads(self.db), *args, **kwargs)
        return await run_in_threadpool(self._run_mock, lambda repo: mock_method(repo, *args, **kwargs))

    async def write(self, operation: Callable[[CompanionWrites | MockCompanions], R]) -> R:
        if self.db is not None:
            return await run_in_threadpool(self._run_db_write, operation)
        return await run_in_threadpool(self._run_mock, operation)

    def _run_db_write(self, operation: Callable[[CompanionWrites], R]) -> R:
        assert isinstance(self.user_id, UUID)
        with service_db_session() as db:
            return operation(CompanionWrites(db, self.user_id))

    def _run_mock(self, operation: Callable[[MockCompanions], R]) -> R:
        assert self.user_id is None or isinstance(self.user_id, str)
        with memory.lock:
            memory.maintenance(rules.now_utc())
            return operation(MockCompanions(memory, self.user_id))


def _mock_user_id(authorization: str) -> str:
    with auth_lock:
        return authenticated_access(authorization, datetime.now(timezone.utc))[1].user_id


async def _get_session(
    user: Annotated[CurrentUser | None, Depends(get_current_user)],
    auth: AuthenticatedSession,
    authorization: Authorization = None,
) -> AsyncIterator[CompanionSession]:
    if not uses_auth_db():
        user_id = await run_in_threadpool(_mock_user_id, authorization) if authorization is not None else None
        yield CompanionSession(user_id)
    elif auth is not None and user is not None:
        yield CompanionSession(user.claims.user_id, auth[1])
    else:
        async with user_db_session() as db:
            yield CompanionSession(None, db)


PublicSession = Annotated[CompanionSession, Depends(_get_session, scope="function")]


async def _require_session(
    user: Annotated[CurrentUser | None, Depends(get_current_user)],
    auth: AuthenticatedSession,
    authorization: Authorization = None,
) -> CompanionSession:
    if not uses_auth_db():
        if authorization is None:
            raise unauthorized()
        return CompanionSession(await run_in_threadpool(_mock_user_id, authorization))
    if user is None or auth is None:
        raise unauthorized()
    return CompanionSession(user.claims.user_id, auth[1])


UserSession = Annotated[CompanionSession, Depends(_require_session)]


@router.get("/festivals/{festival_id}/companion-posts")
async def list_posts(
    festival_id: FestivalId, session: PublicSession,
    status: schema.PostStatus = "open", page: Annotated[int, Query(ge=1)] = 1,
) -> schema.PostList:
    return await session.read(CompanionReads.list_posts, MockCompanions.list_posts, festival_id, status, page)


@router.get("/companion-posts")
async def list_post_feed(
    session: PublicSession,
    festival_id: Annotated[str | None, Query(pattern=schema.FESTIVAL_ID_PATTERN)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    status: schema.PostStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> schema.FeedPostList:
    return await session.read(
        CompanionReads.list_post_feed,
        MockCompanions.list_post_feed,
        festival_id,
        q,
        status,
        page,
        page_size,
    )


@router.post("/companion-posts", status_code=201)
async def create_post(request: schema.PostCreate, session: UserSession) -> schema.PostCreated:
    return await session.write(lambda repo: repo.create_post(request))


@router.get("/companion-posts/{post_id}")
async def get_post(post_id: PostId, session: PublicSession) -> schema.PostDetail:
    return await session.read(CompanionReads.get_post, MockCompanions.get_post, post_id)


@router.patch("/companion-posts/{post_id}")
async def update_post(post_id: PostId, request: schema.PostUpdate, session: UserSession) -> schema.PostChanged:
    return await session.write(lambda repo: repo.update_post(post_id, request))


@router.post("/companion-posts/{post_id}/applications", status_code=201)
async def create_application(
    post_id: PostId, session: UserSession, request: Annotated[schema.ApplicationCreate | None, Body()] = None,
) -> schema.ApplicationCreated:
    return await session.write(lambda repo: repo.create_application(post_id, request or schema.ApplicationCreate()))


@router.get("/companion-posts/{post_id}/applications")
async def list_applications(
    post_id: PostId, session: UserSession, status: schema.VisibleApplicationStatus | None = None,
) -> schema.ApplicationList:
    return await session.read(CompanionReads.list_applications, MockCompanions.list_applications, post_id, status)


@router.post("/companion-applications/{application_id}/{action}")
async def decide_application(
    application_id: ApplicationId, action: schema.ApplicationAction, session: UserSession,
) -> schema.ApplicationChanged:
    return await session.write(lambda repo: repo.decide_application(application_id, action))


@router.put("/companion-posts/{post_id}/meeting-place")
async def set_meeting_place(
    post_id: PostId, request: schema.MeetingPlace, session: UserSession,
) -> schema.MeetingPlaceUpdated:
    return await session.write(lambda repo: repo.set_meeting_place(post_id, request))


@router.get("/companion-posts/{post_id}/meeting-place")
async def get_meeting_place(
    post_id: PostId, session: UserSession,
) -> schema.MeetingPlaceDetail | schema.MeetingPlaceUndecided:
    return await session.read(CompanionReads.get_meeting_place, MockCompanions.get_meeting_place, post_id)


@router.post("/companion-posts/{post_id}/{action}")
async def change_post(
    post_id: PostId, action: schema.PostAction, session: UserSession,
) -> schema.PostChanged:
    return await session.write(lambda repo: repo.change_post(post_id, action))
