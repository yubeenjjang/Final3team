import fcntl
import json
import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, cast

from api.providers.route_base import KST, as_kst

QuotaProvider = Literal["tmap", "kakao", "kakao_local", "seoul_citydata"]

_LIMITS: dict[QuotaProvider, tuple[str, str]] = {
    "tmap": ("ROUTE_TMAP_DAILY_LIMIT", "10"),
    "kakao": ("ROUTE_KAKAO_DAILY_LIMIT", "1000"),
    "kakao_local": ("ROUTE_KAKAO_LOCAL_DAILY_LIMIT", "1000"),
}
_LOGGER = logging.getLogger(__name__)


class QuotaGuard:
    def __init__(self, *, now: Callable[[], datetime] | None = None, crowd: bool = False) -> None:
        limits: dict[QuotaProvider, tuple[str, str]]
        if crowd:
            self._path = Path(os.environ.get("CROWD_QUOTA_FILE", "./.crowd_quota.json"))
            limits = {"seoul_citydata": ("CROWD_SEOUL_DAILY_LIMIT", "1000")}
        else:
            self._path = Path(os.environ.get("ROUTE_QUOTA_FILE", "./.route_quota.json"))
            limits = _LIMITS
        self._lock_path = self._path.with_name(f"{self._path.name}.lock")
        self._limits = {
            provider: int(os.environ.get(env, default))
            for provider, (env, default) in limits.items()
        }
        self._now = now if now is not None else lambda: datetime.now(KST)

    def try_acquire(self, provider: QuotaProvider) -> bool:
        limit = self._limits[provider]
        with self._locked():
            day = self._today()
            counts = self._read(day)
            used = counts.get(provider, 0)
            if used >= limit:
                return False
            counts[provider] = used + 1
            self._write(day, counts)

        if used * 5 <= limit * 4 < (used + 1) * 5:
            _LOGGER.warning("%s 일일 조회 한도를 80%% 넘게 사용했어요.", provider)
        return True

    def status(self) -> dict[QuotaProvider, dict[str, int]]:
        with self._locked():
            counts = self._read(self._today())
        return {
            provider: {"used": counts.get(provider, 0), "limit": limit}
            for provider, limit in self._limits.items()
        }

    def _today(self) -> str:
        return as_kst(self._now()).date().isoformat()

    @contextmanager
    def _locked(self) -> Iterator[None]:
        # 데이터 파일을 교체해도 동일한 파일에 잠금을 걸도록 잠금 파일을 따로 둔다.
        with self._lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _read(self, day: str) -> dict[QuotaProvider, int]:
        try:
            with self._path.open(encoding="utf-8") as data:
                state = json.load(data)
        except FileNotFoundError:
            return {}
        if not isinstance(state, dict):
            raise ValueError("조회 한도 파일의 형식이 올바르지 않아요.")
        counts = state.get("counts")
        if not isinstance(counts, dict):
            raise ValueError("조회 한도 파일의 사용량 형식이 올바르지 않아요.")
        if state["date"] != day:
            return {}
        return cast(dict[QuotaProvider, int], counts)

    def _write(self, day: str, counts: dict[QuotaProvider, int]) -> None:
        with NamedTemporaryFile(
            mode="w", dir=self._path.parent, encoding="utf-8", delete=False
        ) as data:
            pending = Path(data.name)
            try:
                json.dump({"date": day, "counts": counts}, data)
                data.close()
                pending.replace(self._path)
            finally:
                pending.unlink(missing_ok=True)
