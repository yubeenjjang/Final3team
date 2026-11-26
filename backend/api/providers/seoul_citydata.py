import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from urllib.parse import quote

import httpx2

from api.providers.quota import QuotaGuard
from api.providers.route_base import KST
from api.providers.tourapi import _KeyRedactor
from api.schemas.festival_info import CongestColor, CongestLevel, SourceError

_BASE_URL = httpx2.URL(scheme="http", host="openapi.seoul.go.kr", port=8088)
_TIMEOUT_SECONDS = 3.0
_COLORS: dict[CongestLevel, CongestColor] = {
    "여유": "green",
    "보통": "yellow",
    "약간 붐빔": "orange",
    "붐빔": "red",
}


class CityDataError(Exception):
    def __init__(self, message: str, *, retryable: bool) -> None:
        self.error = SourceError(code="SOURCE_RESULT_ERROR", message=message, retryable=retryable)
        super().__init__(message)


@dataclass(frozen=True)
class PopulationReading:
    congest_level: CongestLevel
    congest_color: CongestColor
    congest_message: str
    population_min: int
    population_max: int
    observed_at: datetime
    is_estimate: bool


class SeoulCityData:
    def __init__(self, *, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(self, area_code: str, quota: QuotaGuard) -> PopulationReading:
        key = os.environ.get("SEOUL_OPEN_API_KEY")
        if not key:
            raise CityDataError("서울시 혼잡 조회 키 설정을 확인해 주세요.", retryable=False)
        try:
            acquired = await asyncio.to_thread(quota.try_acquire, "seoul_citydata")
        except (OSError, ValueError, TypeError, KeyError):
            raise CityDataError("서울시 혼잡 조회 한도를 확인할 수 없어요.", retryable=False) from None
        if not acquired:
            raise CityDataError("오늘 서울시 혼잡 조회 한도를 다 썼어요.", retryable=False)

        encoded_key = quote(key, safe="")
        redactor = _KeyRedactor(key, encoded_key)
        path = f"/{encoded_key}/json/citydata_ppltn/1/1/{area_code}"
        with redactor.protect_logs():
            try:
                url = _BASE_URL.copy_with(path=path)
                async with asyncio.timeout(_TIMEOUT_SECONDS):
                    async with httpx2.AsyncClient(
                        transport=self._transport, trust_env=False, timeout=_TIMEOUT_SECONDS
                    ) as client:
                        response = await client.get(url, follow_redirects=False)
            except (TimeoutError, httpx2.TimeoutException):
                raise CityDataError("서울시 혼잡 조회 시간이 초과됐어요.", retryable=True) from None
            except (httpx2.RequestError, httpx2.InvalidURL):
                raise CityDataError("서울시 혼잡 정보를 가져오지 못했어요.", retryable=True) from None

        if response.status_code != 200:
            raise CityDataError(
                "서울시 혼잡 정보를 가져오지 못했어요.",
                retryable=response.status_code >= 500 or response.status_code in (408, 429),
            )
        try:
            return _parse_reading(response.json(), area_code, redactor)
        except (ValueError, TypeError, KeyError):
            raise CityDataError("서울시 혼잡 응답 형식을 확인할 수 없어요.", retryable=True) from None


def _parse_reading(body: Any, area_code: str, redactor: _KeyRedactor) -> PopulationReading:
    if not isinstance(body, dict):
        raise ValueError
    result = body.get("RESULT", body)
    if not isinstance(result, dict):
        raise ValueError
    code = result.get("RESULT.CODE") or result.get("CODE")
    if code != "INFO-000":
        raise CityDataError(
            "서울시에서 혼잡 자료를 가져오지 못했어요.",
            retryable=code not in ("INFO-100", "INFO-200"),
        )

    items = body["SeoulRtd.citydata_ppltn"]
    if not isinstance(items, list) or len(items) != 1:
        raise ValueError
    item = items[0]
    if not isinstance(item, dict) or item.get("AREA_CD") != area_code:
        raise ValueError
    for field in ("AREA_NM", "AREA_CONGEST_LVL", "AREA_CONGEST_MSG", "PPLTN_TIME"):
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ValueError
    level = cast(CongestLevel, item["AREA_CONGEST_LVL"])
    replacement = item["REPLACE_YN"]
    if level not in _COLORS or replacement not in ("N", "Y"):
        raise ValueError

    lower = _population(item["AREA_PPLTN_MIN"])
    upper = _population(item["AREA_PPLTN_MAX"])
    if lower > upper:
        raise ValueError
    observed_at = datetime.strptime(item["PPLTN_TIME"], "%Y-%m-%d %H:%M").replace(tzinfo=KST)
    return PopulationReading(
        congest_level=level,
        congest_color=_COLORS[level],
        congest_message=redactor.redact(item["AREA_CONGEST_MSG"]),
        population_min=lower,
        population_max=upper,
        observed_at=observed_at,
        is_estimate=replacement == "Y",
    )


def _population(value: object) -> int:
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value)
    raise ValueError
