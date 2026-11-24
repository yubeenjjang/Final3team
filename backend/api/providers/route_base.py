import logging
import os
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any, Literal

import httpx2

from api.providers.tourapi import HTTP_LOGGERS

KST = timezone(timedelta(hours=9))
Coordinates = tuple[float, float]
ProviderName = Literal["tmap", "kakao"]
ProviderTier = Literal["primary", "secondary"]
ErrorKind = Literal[
    "config", "no_result", "service_ended", "too_close", "bad_request", "region", "temporary",
    "timeout", "quota",
]

_ERROR_DETAILS: dict[ErrorKind, str] = {
    "config": "공급원 API 키 설정을 확인해 주세요.",
    "no_result": "조건에 맞는 결과가 없어요.",
    "service_ended": "지금은 대중교통으로 갈 수 없어요",
    "too_close": "출발지와 도착지가 너무 가까워요.",
    "bad_request": "공급원에 보낸 요청 값이 올바르지 않아요.",
    "region": "공급원이 지원하는 지역이 아니에요.",
    "temporary": "공급원 응답을 처리할 수 없어요.",
    "timeout": "공급원 응답 시간이 초과됐어요.",
    "quota": "공급원 조회 한도를 다 썼어요.",
}
_private_transport = ContextVar("private_route_transport", default=False)
_logger = logging.getLogger(__name__)


def _allow_transport_log(record: logging.LogRecord) -> bool:
    return not _private_transport.get()


for _name in HTTP_LOGGERS:
    logging.getLogger(_name).addFilter(_allow_transport_log)


@dataclass(frozen=True)
class RouteQuery:
    origin: Coordinates
    destination: Coordinates
    depart_at: datetime | None = None


@dataclass
class ProviderResult:
    provider: ProviderName
    provider_tier: ProviderTier
    queried_at: str
    candidates: list[dict[str, object]]
    notices: list[str]


class ProviderError(Exception):
    def __init__(self, kind: ErrorKind, provider: ProviderName, detail: str | None = None) -> None:
        self.kind = kind
        self.provider = provider
        self.detail = _ERROR_DETAILS[kind] if detail is None else detail
        super().__init__(self.detail)


def as_kst(value: datetime) -> datetime:
    if value.utcoffset() is None:
        return value.replace(tzinfo=KST)
    return value.astimezone(KST)


def minutes(seconds: int | float) -> int:
    return ceil(seconds / 60)


def _summary(legs: list[dict[str, Any]], transfers: int) -> str:
    modes = {"bus": "버스", "subway": "지하철"}
    transit = [modes[leg["mode"]] for leg in legs if leg["mode"] in modes]
    if not transit:
        return "도보"
    label = "·".join(dict.fromkeys(transit))
    if transfers:
        return f"{label} {transfers}회 환승"
    return f"{label} {len(transit)}회"


def make_candidate(
    index: int,
    *,
    duration_min: int,
    distance_m: int,
    walk_m: int | None,
    transfers: int,
    fare_krw: int,
    legs: list[dict[str, Any]],
    service_running: bool | None,
    bus_crowding: dict[str, str],
) -> dict[str, object]:
    return {
        "candidate_id": f"c{index}",
        "summary": _summary(legs, transfers),
        "duration_min": duration_min,
        "distance_m": distance_m,
        "walk_m": walk_m,
        "transfers": transfers,
        "fare_krw": fare_krw,
        "legs": legs,
        "service_running": service_running,
        "score": None,
        "area_evidence": {"crowd_areas": [], "traffic_incidents": []},
        "mode_evidence": {"bus_crowding": bus_crowding},
    }


class RouteProviderClient:
    provider: ProviderName
    _key_env: str
    _timeout: float

    def __init__(self, client: httpx2.Client | None = None) -> None:
        key = os.environ.get(self._key_env)
        if not key:
            raise ProviderError("config", self.provider)
        self._key = key
        self._client = client

    def _request_json(
        self,
        method: str,
        url: httpx2.URL,
        *,
        headers: dict[str, str],
        params: dict[str, str | float | int] | None = None,
        json: dict[str, object] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        if self._client is not None:
            response = self._send(self._client, method, url, headers, params, json)
        else:
            with httpx2.Client() as client:
                response = self._send(client, method, url, headers, params, json)

        status = response.status_code
        _logger.debug("provider=%s http_status=%d", self.provider, status)
        if status in (401, 403):
            raise ProviderError("config", self.provider)
        if status == 429:
            raise ProviderError("quota", self.provider)
        if status not in (200, 400):
            kind: ErrorKind = "bad_request" if 400 <= status < 500 else "temporary"
            raise ProviderError(kind, self.provider)

        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict):
            kind = "bad_request" if status == 400 else "temporary"
            raise ProviderError(kind, self.provider)
        return status, body

    def _send(
        self,
        client: httpx2.Client,
        method: str,
        url: httpx2.URL,
        headers: dict[str, str],
        params: dict[str, str | float | int] | None,
        json: dict[str, object] | None,
    ) -> httpx2.Response:
        # Transport logs can include the URL, header values and encoded payloads.
        token = _private_transport.set(True)
        try:
            return client.request(
                method, url, headers=headers, params=params, json=json,
                timeout=self._timeout, follow_redirects=False,
            )
        except httpx2.TimeoutException:
            kind: ErrorKind = "timeout"
        except (httpx2.RequestError, httpx2.InvalidURL):
            kind = "temporary"
        except UnicodeEncodeError:
            kind = "config"
        finally:
            _private_transport.reset(token)
        # 요청과 응답 원문에는 키가 있을 수 있어 오류에 전달하지 않는다.
        raise ProviderError(kind, self.provider)
