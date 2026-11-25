from collections import deque
from math import ceil
from threading import Lock
from time import monotonic
from typing import Protocol
from uuid import UUID

from ulid import ULID

from api.errors import ApiError
from api.schemas.friends import RequestAction, RequestStatus


def new_request_id() -> str:
    return f"frq_{ULID()}"


def user_not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "신청할 수 있는 사용자를 찾을 수 없습니다.")


def request_not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "친구 신청을 찾을 수 없습니다.")


def blocked() -> ApiError:
    return ApiError(409, "BLOCKED", "이 사용자와 친구 신청을 처리할 수 없습니다.")


def already_friends() -> ApiError:
    return ApiError(409, "ALREADY_FRIENDS", "이미 친구입니다.")


def request_pending() -> ApiError:
    return ApiError(409, "REQUEST_PENDING", "대기 중인 친구 신청이 있습니다.")


def check_request_action(
    actor: UUID, sender: UUID, recipient: UUID, status: RequestStatus, action: RequestAction,
) -> None:
    if actor not in (sender, recipient):
        raise request_not_found()
    if actor != (sender if action == "cancel" else recipient):
        raise ApiError(403, "FORBIDDEN", "이 친구 신청을 처리할 권한이 없습니다.")
    if status != "pending":
        raise ApiError(409, "REQUEST_NOT_PENDING", "이미 처리된 친구 신청입니다.")


class FriendSearchLimiter(Protocol):
    def retry_after(self, user_id: UUID) -> int | None:
        """검색 한 자리를 차지하고, 한도를 넘으면 대기할 초를 반환한다."""
        ...


class MemoryFriendSearchLimiter:
    window_seconds = 60
    limit = 20

    def __init__(self) -> None:
        self._searches: dict[UUID, deque[float]] = {}
        self._lock = Lock()
        self._next_cleanup = 0.0

    def retry_after(self, user_id: UUID) -> int | None:
        with self._lock:
            now = monotonic()
            cutoff = now - self.window_seconds
            if now >= self._next_cleanup:
                self._searches = {
                    uid: times for uid, times in self._searches.items() if times[-1] > cutoff
                }
                self._next_cleanup = now + self.window_seconds
            times = self._searches.setdefault(user_id, deque())
            while times and times[0] <= cutoff:
                times.popleft()
            if len(times) >= self.limit:
                return ceil(times[0] - cutoff)
            times.append(now)
            return None


search_limiter: FriendSearchLimiter = MemoryFriendSearchLimiter()


def enforce_search_limit(user_id: UUID) -> None:
    retry = search_limiter.retry_after(user_id)
    if retry is not None:
        raise ApiError(
            429, "RATE_LIMITED", "친구 검색이 많아 잠시 후 다시 시도해 주세요.",
            retryable=True, retry_after=retry,
        )


def notify_chat_unblocked(blocker_id: UUID, blocked_id: UUID) -> None:
    """채팅 연동 지점. 실제 차단 행이 삭제된 뒤 호출되며 닫힌 방을 재개하지 않는다."""
