import asyncio
import os
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import datetime
from email.utils import parsedate_to_datetime
from functools import cached_property
from time import monotonic
from typing import Any, cast
from urllib.parse import quote, unquote
from xml.etree import ElementTree

import httpx2

from api.providers.quota import QuotaGuard, QuotaProvider
from api.providers.route_base import KST, private_transport_logs
from api.schemas.festival_info import SourceError

DATA_GO_KR = "https://apis.data.go.kr"
DATA_KEY = "DATA_GO_KR_SERVICE_KEY"
_TIMEOUT_S = 3
_RETRY_DELAY_S = 1
_CACHE_MAX_SIZE = 1024


class FestivalSourceError(Exception):
    def __init__(
        self, message: str = "공급원 응답을 처리할 수 없어요.", *,
        http: bool = False, retryable: bool = True, retry_delay: float | None = None,
    ) -> None:
        self.error = SourceError(
            code="SOURCE_HTTP_ERROR" if http else "SOURCE_RESULT_ERROR",
            message=message,
            retryable=retryable,
        )
        self.retry_delay = retry_delay
        super().__init__(message)


class FestivalSource:
    def __init__(
        self, *, transport: httpx2.AsyncBaseTransport | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(KST),
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._transport = transport
        self.now = now
        self._clock = clock
        self._cache: OrderedDict[tuple[str, str], tuple[float, Any]] = OrderedDict()
        self._inflight: dict[tuple[str, str], asyncio.Task[Any]] = {}

    @cached_property
    def _quota(self) -> QuotaGuard:
        return QuotaGuard(now=self.now, info=True)

    async def cached[T](
        self, source: str, target: str, ttl: float, load: Callable[[], Awaitable[T]],
    ) -> T:
        key = (source, target)
        entry = self._cache.get(key)
        if entry is not None:
            if self._clock() < entry[0]:
                self._cache.move_to_end(key)
                return cast(T, entry[1])
            del self._cache[key]

        task = self._inflight.get(key)
        if task is None:
            task = asyncio.create_task(self._load(key, ttl, load))
            task.add_done_callback(self._retrieve_error)
            self._inflight[key] = task
        return cast(T, await asyncio.shield(task))

    @staticmethod
    def _retrieve_error(task: asyncio.Task[Any]) -> None:
        # 취소된 요청만 남았을 때도 asyncio가 공급원 실패를 별도 기록하지 않게 한다.
        if not task.cancelled():
            task.exception()

    async def _load[T](self, key: tuple[str, str], ttl: float, load: Callable[[], Awaitable[T]]) -> T:
        try:
            result = await load()
            self._cache[key] = (self._clock() + ttl, result)
            if len(self._cache) > _CACHE_MAX_SIZE:
                self._cache.popitem(last=False)
            return result
        finally:
            self._inflight.pop(key, None)

    async def request[T](
        self, source: QuotaProvider, endpoint: str, parse: Callable[[dict[str, Any]], T], *,
        params: dict[str, str | int | float] | None = None, key_env: str = DATA_KEY,
    ) -> T:
        raw_key = os.environ.get(key_env, "").strip()
        if not raw_key:
            raise FestivalSourceError("공급원 API 키 설정을 확인해 주세요.", retryable=False)
        key = unquote(raw_key)
        if "{key}" in endpoint:
            url = endpoint.replace("{key}", quote(key, safe=""))
        else:
            url = endpoint
            params = {**(params or {}), "serviceKey": key}

        for attempt in range(2):
            try:
                response = await self._send(source, url, params)
                return self._parse(response, parse)
            except FestivalSourceError as exc:
                delay = exc.retry_delay if exc.retry_delay is not None else _RETRY_DELAY_S
                # 긴 Retry-After는 요청을 붙들지 않고 호출자에게 일시 오류를 반환한다.
                if attempt or not exc.error.retryable or delay > _TIMEOUT_S:
                    raise
            await asyncio.sleep(delay)
        raise AssertionError("외부 조회 시도가 끝났습니다.")

    async def _send(
        self, source: QuotaProvider, url: str, params: dict[str, str | int | float] | None,
    ) -> httpx2.Response:
        try:
            acquired = await asyncio.to_thread(lambda: self._quota.try_acquire(source))
        except (OSError, ValueError, TypeError, KeyError):
            raise FestivalSourceError("공급원 조회 한도를 확인할 수 없어요.", retryable=False) from None
        if not acquired:
            raise FestivalSourceError("오늘 공급원 조회 한도를 다 썼어요.", retryable=False)
        with private_transport_logs():
            try:
                async with asyncio.timeout(_TIMEOUT_S):
                    async with httpx2.AsyncClient(
                        transport=self._transport, trust_env=False, timeout=_TIMEOUT_S,
                    ) as client:
                        return await client.get(url, params=params, follow_redirects=False)
            except (TimeoutError, httpx2.TimeoutException):
                raise FestivalSourceError("공급원 응답 시간이 초과됐어요.", http=True) from None
            except (httpx2.RequestError, httpx2.InvalidURL, UnicodeError):
                raise FestivalSourceError("공급원 요청에 실패했어요.", http=True) from None

    def _parse[T](self, response: httpx2.Response, parse: Callable[[dict[str, Any]], T]) -> T:
        status = response.status_code
        if status != 200:
            raise FestivalSourceError(
                "공급원 요청에 실패했어요.", http=True,
                retryable=status in (408, 429) or status >= 500,
                retry_delay=self._retry_after(response) if status == 429 else None,
            )
        try:
            try:
                body = response.json()
            except ValueError:
                root = ElementTree.fromstring(response.content)
                code = root.findtext(".//returnReasonCode")
                if code is not None:
                    raise _result_error(code)
                raise ValueError
            if not isinstance(body, dict):
                raise ValueError
            common_error = body.get("OpenAPI_ServiceResponse")
            if isinstance(common_error, dict):
                raise _result_error(str(common_error["cmmMsgHeader"]["returnReasonCode"]))
            return parse(body)
        except (ValueError, TypeError, KeyError, OverflowError, ElementTree.ParseError):
            raise FestivalSourceError(retryable=False) from None

    def _retry_after(self, response: httpx2.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if value is None:
            return None
        try:
            if value.isascii() and value.isdecimal():
                return float(value)
            return max(0, (parsedate_to_datetime(value) - self.now()).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None


def _result_error(code: str) -> FestivalSourceError:
    if code in {"22", "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"}:
        return FestivalSourceError("공급원 조회 한도를 다 썼어요.", retryable=False)
    return FestivalSourceError(
        retryable=code in {"01", "02", "04", "05", "99", "1", "2", "4", "5"},
    )


def item_list(value: Any) -> list[dict[str, Any]]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError
    return value


def public_items(body: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    response = body["response"]
    code = str(response["header"]["resultCode"])
    if code in ("03", "3"):
        return [], 0
    if code not in ("00", "0", "0000"):
        raise _result_error(code)
    data = response["body"]
    container = data.get("items")
    # TAGO/TourAPI의 빈 결과는 items가 빈 문자열로 온다.
    rows = item_list(container.get("item") if isinstance(container, dict) else container)
    total = int(data.get("totalCount", len(rows)))
    if total < len(rows) or (total > 0 and not rows):
        raise ValueError
    return rows, total
