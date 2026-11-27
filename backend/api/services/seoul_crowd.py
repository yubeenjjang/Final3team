import asyncio
import os
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import cached_property, lru_cache
from math import isfinite
from time import monotonic

from api.errors import ApiError
from api.providers.quota import QuotaGuard
from api.providers.route_base import KST, as_kst
from api.providers.seoul_citydata import CityDataError, PopulationReading, SeoulCityData
from api.schemas.festival_info import (
    Coverage,
    CrowdArea,
    NearbyCrowdArea,
    RealCrowdResponse,
    SourceError,
    build_crowd_geometry,
)
from api.services.festival_lookup import find_festival
from api.services.seoul_areas import SeoulArea, area_geometry, classify_areas, load_catalog, nearby_areas
from api.services.seoul_crowd_mapping import approved_area_codes, needs_human_review

_CACHE_SECONDS = 60
_STALE_AFTER = timedelta(minutes=45)
_OBSERVED_LABEL = "주변 지역 혼잡(서울시 실시간 도시데이터)"
_VENUE_NOTICE = "행사장 안 혼잡과 다를 수 있어요"


def uses_real_crowd() -> bool:
    return os.environ.get("CROWD_PROVIDER", "mock") == "real"


class SeoulCrowdService:
    def __init__(
        self,
        provider: SeoulCityData,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(KST),
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._provider = provider
        self._now = now
        self._clock = clock
        self._cache: dict[str, tuple[float, PopulationReading]] = {}
        self._inflight: dict[str, asyncio.Task[PopulationReading | SourceError]] = {}

    @cached_property
    def _quota(self) -> QuotaGuard:
        return QuotaGuard(now=self._now, crowd=True)

    async def get_crowd(self, festival_id: str) -> RealCrowdResponse:
        festival = await find_festival(festival_id)
        if festival is None:
            raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")

        catalog = load_catalog()
        is_seoul = festival.region_code == "SEOUL"
        response = RealCrowdResponse(
            festival_id=festival_id,
            status="unsupported",
            coverage=Coverage(scope="seoul_only", region_code=festival.region_code, supported=is_seoul),
            source="seoul_citydata",
            source_url=catalog.source_url,
        )
        if not is_seoul:
            response.unsupported_reason = "outside_seoul"
            response.notices.append("이 지역은 아직 지원하지 않아요")
            return response
        lat, lng = festival.lat, festival.lng
        if lat is None or lng is None or not (
            isfinite(lat) and isfinite(lng) and abs(lat) <= 90 and abs(lng) <= 180
        ):
            response.unsupported_reason = "missing_coordinates"
            response.notices.append("축제 위치를 확인할 수 없어요.")
            return response
        approved_codes = approved_area_codes(festival)
        if approved_codes:
            approved_areas = tuple(area for area in catalog.areas if area.code in approved_codes)
            matches = nearby_areas(lat, lng, approved_areas)
            if not matches:
                response.unsupported_reason = "no_nearby_areas"
                response.notices.append("축제에서 1km 이내에 승인된 주변 지역 혼잡 구역이 없어요.")
                return response
        elif needs_human_review(festival):
            response.unsupported_reason = "no_approved_mapping"
            response.notices.append("여러 장소에서 열리거나 장소 확인이 필요한 축제라 확인 후 주변 지역 혼잡을 연결할 예정이에요.")
            return response
        else:
            classification = classify_areas(lat, lng, catalog.areas)
            if classification.auto_areas:
                matches = [(area, 0.0) for area in classification.auto_areas]
            elif classification.near_boundary:
                response.unsupported_reason = "no_approved_mapping"
                response.notices.append("관측 구역 경계 근처 축제라 확인 후 주변 지역 혼잡을 연결할 예정이에요.")
                return response
            else:
                response.unsupported_reason = "no_nearby_areas"
                response.notices.append("이 축제는 서울시 실시간 혼잡 관측 구역(121곳) 범위 밖이에요.")
                return response

        response.nearby_areas = await asyncio.gather(
            *(self._area_result(area, distance) for area, distance in matches)
        )
        successful = [area for area in response.nearby_areas if area.data is not None]
        if not successful:
            errors = [area.error for area in response.nearby_areas if area.error is not None]
            response.status = "unavailable"
            response.error = errors[0] if all(error == errors[0] for error in errors) else SourceError(
                code="SOURCE_RESULT_ERROR",
                message="서울시 혼잡 정보를 가져오지 못했어요.",
                retryable=any(error.retryable for error in errors),
            )
            return response

        primary = successful[0]
        assert primary.data is not None
        response.status = primary.status
        response.areas = [primary.data]
        response.observed_at = primary.data.observed_at
        response.is_estimate = primary.is_estimate
        response.notices = [
            _VENUE_NOTICE,
            "출처 서울특별시 · 2026년 서울시 인구데이터 (OA-21778)",
        ]
        for area in successful:
            assert area.data is not None
            timestamp = area.data.observed_at.strftime("%Y-%m-%d %H:%M KST")
            notice = f"{_OBSERVED_LABEL} · {area.area_name} · {area.distance_m:g}m · 기준 {timestamp}"
            if area.status == "stale":
                notice += " · 정보가 오래됐어요"
            response.notices.append(notice)
        return response

    async def _area_result(self, area: SeoulArea, distance: float) -> NearbyCrowdArea:
        distance_m = max(0.1, round(distance, 1)) if distance > 0 else 0.0
        center, boundary = build_crowd_geometry(*area_geometry(area))
        reading = await self._reading(area.code)
        if isinstance(reading, SourceError):
            return NearbyCrowdArea(
                area_code=area.code, area_name=area.name, distance_m=distance_m,
                status="unavailable", error=reading,
                center=center, boundary=boundary,
            )
        return NearbyCrowdArea(
            area_code=area.code,
            area_name=area.name,
            distance_m=distance_m,
            status="stale" if as_kst(self._now()) - reading.observed_at > _STALE_AFTER else "ok",
            is_estimate=reading.is_estimate,
            center=center,
            boundary=boundary,
            data=CrowdArea(
                area_code=area.code,
                area_name=area.name,
                relation_type="contains" if distance == 0 else "adjacent",
                congest_level=reading.congest_level,
                congest_color=reading.congest_color,
                congest_message=reading.congest_message,
                population_min=reading.population_min,
                population_max=reading.population_max,
                observed_at=reading.observed_at,
                forecast=[],
                center=center,
                boundary=boundary,
            ),
        )

    async def _reading(self, area_code: str) -> PopulationReading | SourceError:
        cached = self._cache.get(area_code)
        if cached is not None and self._clock() < cached[0]:
            return cached[1]
        self._cache.pop(area_code, None)
        task = self._inflight.get(area_code)
        if task is None:
            task = asyncio.create_task(self._fetch(area_code))
            self._inflight[area_code] = task
        # 한 요청이 취소되어도 병합된 다른 요청의 조회는 계속한다.
        return await asyncio.shield(task)

    async def _fetch(self, area_code: str) -> PopulationReading | SourceError:
        try:
            try:
                quota = self._quota
            except ValueError:
                raise CityDataError("서울시 혼잡 조회 한도 설정을 확인해 주세요.", retryable=False) from None
            reading = await self._provider.fetch(area_code, quota)
            if reading.is_estimate:
                raise CityDataError("서울시 주변 지역 혼잡 관측 자료를 가져오지 못했어요.", retryable=True)
            if reading.observed_at > as_kst(self._now()):
                raise CityDataError("서울시 혼잡 기준 시각을 확인할 수 없어요.", retryable=True)
            self._cache[area_code] = (self._clock() + _CACHE_SECONDS, reading)
            return reading
        except CityDataError as exc:
            return exc.error
        finally:
            self._inflight.pop(area_code, None)


@lru_cache(maxsize=1)
def get_service() -> SeoulCrowdService:
    return SeoulCrowdService(SeoulCityData())
