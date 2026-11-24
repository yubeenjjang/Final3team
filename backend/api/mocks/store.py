from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from threading import Lock

from api.ingestion.festivals.normalize import FESTIVAL_CATEGORY
from api.mocks.festivals import FESTIVALS, MockFestival
from api.schemas.assistant import AssistantRequest
from api.schemas.festivals import FestivalDetail
from api.schemas.routes import RouteDirection, RouteRequest, RouteStatus
from api.schemas.users import FestivalPreferences


@dataclass
class RouteRecord:
    route_request_id: str
    access_token: str = field(repr=False)
    direction: RouteDirection
    request: RouteRequest
    festival: FestivalDetail
    body: str
    scenario: str
    status: RouteStatus
    updated_at: str
    control_version: str


festivals: dict[str, MockFestival] = {}


def public_mock_festivals() -> Iterator[MockFestival]:
    return (festival for festival in festivals.values() if festival.category == FESTIVAL_CATEGORY)


def get_public_mock_festival(festival_id: str) -> MockFestival | None:
    festival = festivals.get(festival_id)
    return festival if festival is not None and festival.category == FESTIVAL_CATEGORY else None


route_requests: dict[str, RouteRecord] = {}
route_request_keys: dict[tuple[RouteDirection, str], str] = {}
route_lock = Lock()


@dataclass
class AssistantRun:
    run_id: str
    conversation_id: str
    access_token: str = field(repr=False)
    request: AssistantRequest
    body: str
    queued_at: str
    started_at: str | None = None
    ended_at: str | None = None
    outcome: dict[str, object] | None = field(default=None, repr=False)


@dataclass(frozen=True)
class MockUser:
    user_id: str
    display_name: str
    salt: bytes = field(repr=False)
    password_hash: bytes = field(repr=False)
    birth_year: int
    gender: str
    disabled: bool = False


@dataclass(frozen=True)
class AccessSession:
    user_id: str
    expires_at: datetime


@dataclass(frozen=True)
class RefreshSession:
    user: MockUser
    expires_at: datetime


assistant_conversations: set[str] = set()
assistant_runs: dict[str, AssistantRun] = {}
assistant_request_keys: dict[str, str] = {}
assistant_lock = Lock()

users_by_email: dict[str, MockUser] = {}
user_nicknames: set[str] = set()
access_sessions: dict[str, AccessSession] = {}
refresh_sessions: dict[str, RefreshSession] = {}
retired_refresh_tokens: dict[str, str] = {}
auth_lock = Lock()


@dataclass(frozen=True)
class FavoriteRecord:
    saved_at: datetime
    sequence: int


favorites_by_user: dict[str, dict[str, FavoriteRecord]] = {}
preferences_by_user: dict[str, FestivalPreferences] = {}
favorite_sequence = count()


def reset_store() -> None:
    with assistant_lock, route_lock, auth_lock:
        festivals.clear()
        festivals.update(
            (festival.festival_id, festival.model_copy(deep=True)) for festival in FESTIVALS
        )
        route_requests.clear()
        route_request_keys.clear()
        assistant_conversations.clear()
        assistant_runs.clear()
        assistant_request_keys.clear()
        users_by_email.clear()
        user_nicknames.clear()
        access_sessions.clear()
        refresh_sessions.clear()
        retired_refresh_tokens.clear()
        favorites_by_user.clear()
        preferences_by_user.clear()


reset_store()
