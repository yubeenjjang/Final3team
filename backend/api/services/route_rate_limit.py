"""A04·A25 share the same minute buckets."""

import hmac
from datetime import datetime, timezone
from secrets import token_bytes
from typing import Protocol

from api.auth.state import MemoryAuthState
from api.auth.tokens import positive_setting, read_access_token, uses_auth_db
from api.errors import ApiError
from api.mocks.store import auth_lock
from api.services.mock_auth import authenticated_access

_WINDOW_S = 60
_HASH_KEY = token_bytes(32)


class CounterState(Protocol):
    def increment(self, key: str, ttl_s: int) -> int: ...


state: CounterState = MemoryAuthState()


def _session(authorization: str | None, now: datetime) -> str | None:
    if authorization is None:
        return None
    try:
        if uses_auth_db():
            return read_access_token(authorization).jti
        with auth_lock:
            return authenticated_access(authorization, now)[0]
    except (ApiError, ValueError):
        # These endpoints also accept anonymous traffic.
        return None


def enforce(ip: str, authorization: str | None) -> None:
    now = datetime.now(timezone.utc)
    session = _session(authorization, now)
    identities = [f"ip:{ip}"]
    if session is not None:
        identities.append(f"session:{session}")
    limit = positive_setting("ROUTE_RATE_LIMIT_PER_MIN", 10)
    counts = []
    for identity in identities:
        digest = hmac.digest(_HASH_KEY, identity.encode(), "sha256").hex()
        key = f"rl:route:{digest}:{now:%Y%m%d%H%M}"
        counts.append(state.increment(key, _WINDOW_S))
    if max(counts) > limit:
        raise ApiError(
            429, "RATE_LIMITED", "경로 요청이 많아 잠시 후 다시 시도해 주세요.",
            retryable=True, retry_after=_WINDOW_S - now.second,
        )
