import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Protocol

from api.auth.tokens import login_ip_hash, positive_setting
from api.errors import ApiError

_RATE_WINDOW_S = 60


class AuthStateUnavailable(RuntimeError):
    """인증 상태 저장소 어댑터의 연결·처리 오류."""


class AuthState(Protocol):
    def is_revoked(self, jti: str) -> bool: ...
    def revoke(self, jti: str, ttl_s: int) -> None: ...
    def count_login(self, key: str, ttl_s: int) -> int: ...
    def lock_refresh(self, token_id: str, owner: str, ttl_s: int) -> bool: ...
    def unlock_refresh(self, token_id: str, owner: str) -> None: ...


@dataclass
class _Entry:
    value: str | int
    deadline: float


class MemoryAuthState:
    """Redis가 연결되기 전까지 한 API 프로세스가 공유하는 TTL 저장소."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        self._lock = Lock()
        self._next_cleanup = 0.0

    def _get(self, key: str, now: float) -> _Entry | None:
        if now >= self._next_cleanup:
            self._entries = {
                key: entry for key, entry in self._entries.items() if entry.deadline > now
            }
            self._next_cleanup = now + _RATE_WINDOW_S
        entry = self._entries.get(key)
        if entry is not None and entry.deadline <= now:
            del self._entries[key]
            return None
        return entry

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            return self._get(f"revoked:{jti}", monotonic()) is not None

    def revoke(self, jti: str, ttl_s: int) -> None:
        with self._lock:
            now = monotonic()
            key = f"revoked:{jti}"
            self._get(key, now)
            self._entries[key] = _Entry(1, now + ttl_s)

    def count_login(self, key: str, ttl_s: int) -> int:
        with self._lock:
            now = monotonic()
            entry = self._get(key, now)
            if entry is None:
                entry = _Entry(0, now + ttl_s)
                self._entries[key] = entry
            entry.value = int(entry.value) + 1
            return entry.value

    def lock_refresh(self, token_id: str, owner: str, ttl_s: int) -> bool:
        with self._lock:
            now = monotonic()
            key = f"refresh:lock:{token_id}"
            if self._get(key, now) is not None:
                return False
            self._entries[key] = _Entry(owner, now + ttl_s)
            return True

    def unlock_refresh(self, token_id: str, owner: str) -> None:
        with self._lock:
            key = f"refresh:lock:{token_id}"
            entry = self._get(key, monotonic())
            if entry is not None and entry.value == owner:
                del self._entries[key]


_auth_state = MemoryAuthState()


def get_auth_state() -> AuthState:
    return _auth_state


def auth_check_unavailable() -> ApiError:
    return ApiError(503, "AUTH_CHECK_UNAVAILABLE", "인증 상태를 확인할 수 없습니다.", retryable=True)


def enforce_login_limit(ip: str) -> None:
    now = datetime.now(timezone.utc)
    ip_hash = login_ip_hash(ip)
    key = f"rl:auth:{ip_hash}:{now:%Y%m%d%H%M}"
    try:
        count = get_auth_state().count_login(key, _RATE_WINDOW_S)
    except AuthStateUnavailable:
        raise auth_check_unavailable() from None
    if count > positive_setting("AUTH_RATE_LIMIT_PER_MIN", 10):
        raise ApiError(
            429, "RATE_LIMITED", "로그인 요청이 많아 잠시 후 다시 시도해 주세요.",
            retryable=True, retry_after=_RATE_WINDOW_S - now.second,
        )


def refresh_in_progress() -> ApiError:
    return ApiError(409, "REFRESH_IN_PROGRESS", "이미 토큰을 갱신하고 있습니다.", retryable=True)


@contextmanager
def refresh_lock(token_id: str) -> Iterator[None]:
    state = get_auth_state()
    owner = secrets.token_hex(16)
    try:
        acquired = state.lock_refresh(token_id, owner, positive_setting("REFRESH_LOCK_TTL_S", 5))
    except AuthStateUnavailable:
        raise auth_check_unavailable() from None
    if not acquired:
        raise refresh_in_progress()
    try:
        yield
    finally:
        try:
            state.unlock_refresh(token_id, owner)
        except AuthStateUnavailable:
            # 교체가 이미 커밋됐다면 응답을 전달합니다. 잠금은 TTL로 해제됩니다.
            pass
