import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Literal

from sqlalchemy.exc import SQLAlchemyError

from api.errors import ApiError
from api.providers import kma_weather, traffic_incidents, transit_arrivals, visit_forecast
from api.providers.festival_source import FestivalSource, FestivalSourceError
from api.providers.route_base import as_kst
from api.repositories import festival_info as repository
from api.repositories.festival_info import FacilityStation
from api.schemas.festival_info import (
    Coverage, FailedWeatherForecast, InfoResponse, NoticeResponse, NoticeType, SourceError,
    TrafficIncidentResponse, TrafficIncidentType, TransitArrival, TransitMode, TransitResponse,
    TransitStation, VisitForecast, VisitForecastResponse,
    WeatherResponse,
)
from api.schemas.festivals import FestivalDetail
from api.services.festival_lookup import find_festival
from api.services.notice_lookup import uses_notice_db

ModeName = Literal["notices", "weather", "transit", "traffic-incidents", "visit-forecast"]
_PROVIDER_ENVS: dict[ModeName, str] = {
    "notices": "NOTICES_PROVIDER", "weather": "WEATHER_PROVIDER",
    "transit": "TRANSIT_PROVIDER", "traffic-incidents": "TRAFFIC_INCIDENT_PROVIDER",
    "visit-forecast": "VISIT_FORECAST_PROVIDER",
}
_DB_ERRORS = (SQLAlchemyError, RuntimeError, ValueError)
_STALE_NOTICE = "정보가 오래됐어요"
_NO_FORECAST = "이 축제 장소의 예측 자료가 없어요"


def uses_real_info(name: str) -> bool:
    if name == "notices":
        return uses_notice_db()
    env = _PROVIDER_ENVS.get(name)
    return env is not None and os.environ.get(env, "mock") == "real"


def _mark_error(response: InfoResponse, error: SourceError) -> None:
    response.status = "unavailable"
    response.error = error


def _unknown_location(response: InfoResponse) -> None:
    _mark_error(response, SourceError(
        code="FESTIVAL_LOCATION_UNKNOWN", message="축제 위치를 확인할 수 없어요.", retryable=False,
    ))


def _stale(response: InfoResponse) -> None:
    response.status = "stale"
    response.notices.append(_STALE_NOTICE)
    response.error = SourceError(code="SOURCE_STALE", message=_STALE_NOTICE, retryable=False)


def _coverage(festival: FestivalDetail, seoul_only: bool = False) -> Coverage:
    return Coverage(
        scope="seoul_only" if seoul_only else "national", region_code=festival.region_code,
        supported=not seoul_only or festival.region_code == "SEOUL",
    )


def _coordinates(festival: FestivalDetail) -> tuple[float, float] | None:
    lat, lng = festival.lat, festival.lng
    if lat is not None and lng is not None and 33 <= lat <= 39 and 124 <= lng <= 132:
        return lat, lng
    return None


def _format_error(message: str, *, retryable: bool = False) -> SourceError:
    return SourceError(code="SOURCE_RESULT_ERROR", message=message, retryable=retryable)


class FestivalInfoService:
    def __init__(self, source: FestivalSource) -> None:
        self.source = source

    def _now(self) -> datetime:
        return as_kst(self.source.now())

    async def _festival(self, festival_id: str) -> FestivalDetail:
        festival = await find_festival(festival_id)
        if festival is None:
            raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
        return festival

    async def notices(
        self, festival_id: str, notice_type: NoticeType | None, active_only: bool,
    ) -> NoticeResponse:
        festival = await self._festival(festival_id)
        response = NoticeResponse(festival_id=festival_id, source="operator", coverage=_coverage(festival), is_mock=False)
        now = self._now()
        try:
            response.items = await repository.approved_notices(festival_id, notice_type, active_only, now)
        except _DB_ERRORS:
            _mark_error(response, _format_error("승인된 공지를 조회할 수 없어요.", retryable=True))
            return response
        response.observed_at = now
        if not response.items:
            response.notices.append("확인할 수 있는 공지 자료가 없어요")
        return response

    async def weather(self, festival_id: str) -> WeatherResponse:
        festival = await self._festival(festival_id)
        response = WeatherResponse(festival_id=festival_id, source="kma", coverage=_coverage(festival), is_mock=False)
        coordinates = _coordinates(festival)
        if coordinates is None:
            _unknown_location(response)
            return response
        grid = kma_weather.weather_grid(*coordinates)
        try:
            current = await kma_weather.current_weather(self.source, grid)
        except FestivalSourceError as exc:
            _mark_error(response, exc.error)
            return response

        try:
            forecast = await kma_weather.short_forecast(self.source, grid)
        except FestivalSourceError as exc:
            forecast = FailedWeatherForecast(error=exc.error)
        response.observed_at = current.observed_at
        response.data = current.model_copy(update={"forecast": forecast})
        if self._now() - current.observed_at > timedelta(hours=2):
            _stale(response)
        return response

    async def transit(self, festival_id: str, mode: TransitMode, radius_m: int, limit: int) -> TransitResponse:
        festival = await self._festival(festival_id)
        is_seoul = festival.region_code == "SEOUL"
        if mode == "subway":
            source = "seoul_subway"
        else:
            source = "seoul_bus_arrival" if is_seoul else "tago_bus"
        response = TransitResponse(
            festival_id=festival_id, coverage=_coverage(festival, mode == "subway"), source=source, is_mock=False,
        )
        coordinates = _coordinates(festival)
        if coordinates is None:
            _unknown_location(response)
            return response
        if not response.coverage.supported:
            response.status = "unsupported"
            response.error = SourceError(
                code="REGION_UNSUPPORTED", message="이 지역은 아직 지원하지 않아요", retryable=False,
            )
            return response
        try:
            facilities = await repository.nearby_facilities(*coordinates, radius_m, mode)
        except _DB_ERRORS:
            _mark_error(response, _format_error("주변 정류장·역 위치를 조회할 수 없어요.", retryable=True))
            return response

        candidates = sorted(
            ((transit_arrivals.distance_m(*coordinates, facility.lat, facility.lng), facility) for facility in facilities),
            key=lambda pair: (pair[0], pair[1].station_id),
        )
        nearby = [(distance, facility) for distance, facility in candidates if distance <= radius_m][:limit]
        if not nearby:
            response.status = "unverified"
            response.notices.append("확인할 수 있는 주변 정류장·역 위치가 없어요.")
            return response

        results = await asyncio.gather(
            *(self._station(facility, distance, is_seoul) for distance, facility in nearby)
        )
        response.stations = [station for station, _ in results]
        errors = [error for _, error in results if error is not None]
        timestamps = [station.observed_at for station in response.stations if station.observed_at is not None]
        if timestamps:
            response.observed_at = min(timestamps)
            if self._now() - response.observed_at > timedelta(seconds=2 * transit_arrivals.ARRIVAL_TTL_S):
                _stale(response)
        elif errors:
            error = errors[0] if all(error == errors[0] for error in errors) else _format_error(
                "대중교통 도착 정보를 가져오지 못했어요.", retryable=any(error.retryable for error in errors),
            )
            _mark_error(response, error)
        elif all(station.status == "unsupported" for station in response.stations):
            response.status = "unsupported"
        else:
            response.status = "unverified"
        return response

    async def _station(
        self, facility: FacilityStation, distance: float, festival_in_seoul: bool,
    ) -> tuple[TransitStation, SourceError | None]:
        station = TransitStation(
            type=facility.type, station_id=facility.station_id, name=facility.name,
            lat=facility.lat, lng=facility.lng, distance_m=round(distance, 1),
        )
        in_seoul = facility.region_code == "SEOUL" if facility.region_code else festival_in_seoul
        try:
            if facility.type == "subway":
                if not in_seoul:
                    station.status = "unsupported"
                    return station, None
                reading = await transit_arrivals.subway_arrivals(self.source, facility.name)
            elif in_seoul:
                reading = await self._seoul_bus(facility)
            else:
                reading = await self._tago_bus(facility)
        except FestivalSourceError as exc:
            station.status = "unavailable"
            return station, exc.error
        if reading is None:
            station.status = "unverified"
        else:
            station.arrivals = reading.arrivals
            station.observed_at = reading.observed_at
        return station, None

    async def _tago_bus(self, facility: FacilityStation) -> transit_arrivals.ArrivalReading | None:
        node_id = facility.source_item_id
        if facility.source_id not in {"tago_bus", "tago_stop", "tago_bus_stop"}:
            return None
        city_code, separator, node_ref = (facility.ref_code or "").partition(":")
        if not (separator and city_code.isascii() and city_code.isdecimal() and node_ref == node_id):
            city_code = await transit_arrivals.tago_city_code(self.source, node_id, facility.lat, facility.lng)
        if not city_code:
            return None
        return await transit_arrivals.tago_arrivals(self.source, city_code, node_id)

    async def _seoul_bus(self, facility: FacilityStation) -> transit_arrivals.ArrivalReading | None:
        ars_id = facility.ref_code
        if not (ars_id and len(ars_id) == 5 and ars_id.isascii() and ars_id.isdecimal()):
            return None

        rows, observed_at = await transit_arrivals.seoul_station_rows(self.source, ars_id)
        matching = [
            row for row in rows if transit_arrivals.matches_seoul_id(row, ars_id, facility.source_item_id)
        ]
        if rows and not matching:
            return None

        async def enrich(row: dict[str, Any]) -> TransitArrival:
            route_id = row.get("busRouteId")
            if not route_id:
                return transit_arrivals.seoul_bus_arrival(row, False)
            try:
                route_rows = await transit_arrivals.seoul_route_rows(self.source, str(route_id))
            except FestivalSourceError:
                return transit_arrivals.seoul_bus_arrival(row, False)
            candidates = [candidate for candidate in route_rows if str(candidate.get("busRouteId")) == str(route_id)]
            crowding_row = transit_arrivals.match_seoul_stop(
                candidates, ars_id=ars_id, node_id=facility.source_item_id, name=facility.name,
                lat=facility.lat, lng=facility.lng, line=str(row["rtNm"]),
                direction=str(row.get("dir") or "").strip() or None,
            )
            if crowding_row is None:
                return transit_arrivals.seoul_bus_arrival(row, False)
            return transit_arrivals.seoul_bus_arrival(crowding_row, True)

        arrivals = await asyncio.gather(*(enrich(row) for row in matching))
        return transit_arrivals.ArrivalReading(arrivals, observed_at)

    async def traffic(
        self, festival_id: str, radius_m: int, kind: TrafficIncidentType | None,
    ) -> TrafficIncidentResponse:
        festival = await self._festival(festival_id)
        response = TrafficIncidentResponse(
            festival_id=festival_id, coverage=_coverage(festival), source="police_incident", is_mock=False,
        )
        coordinates = _coordinates(festival)
        if coordinates is None:
            _unknown_location(response)
            return response

        async def fetch(
            load: Callable[[FestivalSource], Awaitable[traffic_incidents.IncidentReading]],
        ) -> traffic_incidents.IncidentReading | SourceError:
            try:
                return await load(self.source)
            except FestivalSourceError as exc:
                return exc.error

        nationwide = [fetch(traffic_incidents.public_incidents)]
        if traffic_incidents.utic_enabled():
            nationwide.append(fetch(traffic_incidents.utic_incidents))
        local = []
        if festival.region_code == "SEOUL" and os.environ.get(traffic_incidents.SEOUL_KEY, "").strip():
            local.append(fetch(traffic_incidents.topis_incidents))

        results = await asyncio.gather(*nationwide, *local)
        readings = [result for result in results if isinstance(result, traffic_incidents.IncidentReading)]
        if not readings:
            errors = [result for result in results if isinstance(result, SourceError)]
            _mark_error(response, next((error for error in errors if error.retryable), errors[0]))
            return response

        response.source = readings[0].source
        if response.source == "seoul_topis":
            response.coverage = _coverage(festival, seoul_only=True)
            response.notices.append("전국 교통 돌발을 확인할 수 없어 서울 TOPIS 정보만 표시해요.")
        if local and isinstance(results[-1], SourceError):
            response.notices.append("서울 TOPIS 정보를 가져오지 못했어요.")
        response.observed_at = min(reading.observed_at for reading in readings)
        response.items = traffic_incidents.nearby_incidents(readings, coordinates, radius_m, kind)
        if self._now() - response.observed_at > timedelta(seconds=2 * traffic_incidents.INCIDENT_TTL_S):
            _stale(response)
        return response

    async def forecast(self, festival_id: str, days: int) -> VisitForecastResponse:
        festival = await self._festival(festival_id)
        response = VisitForecastResponse(
            festival_id=festival_id, coverage=_coverage(festival), source="visit_forecast",
            is_mock=False, forecast=VisitForecast(status="unsupported"),
        )
        try:
            match = visit_forecast.find_attraction(festival_id, festival.venue_name)
            if match is None:
                response.status = "unsupported"
                response.notices.append(_NO_FORECAST)
                return response
            now = self._now()
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month = (since - timedelta(days=since.day)).strftime("%Y%m")
            district = f"{match.area_code}:{match.district_code}"

            async def fetch_attraction() -> visit_forecast.TourReading:
                reading = await visit_forecast.fetch_district_forecast(self.source, match)
                reading = visit_forecast.attraction_rows(reading, match)
                visit_forecast.forecast_days(reading)
                return reading

            forecast_result, demand_result = await asyncio.gather(
                self._tour_reading(
                    "visit_forecast", f"{district}:{match.attraction}", festival.region_code, since, fetch_attraction,
                ),
                self._tour_reading(
                    "region_demand", f"{district}:{month}", festival.region_code, since,
                    lambda: visit_forecast.fetch_region_demand(self.source, match, month),
                ),
                return_exceptions=True,
            )
            if isinstance(forecast_result, BaseException):
                raise forecast_result
            if isinstance(demand_result, visit_forecast.TourReading):
                response.region_demand = visit_forecast.region_demand(demand_result)
            elif isinstance(demand_result, (FestivalSourceError, *_DB_ERRORS)):
                response.notices.append("지역별 관광 수요를 가져오지 못했어요.")
            else:
                raise demand_result
            forecast_days = visit_forecast.forecast_days(forecast_result)
        except FestivalSourceError as exc:
            _mark_error(response, exc.error)
            response.forecast.status = "unavailable"
            return response
        except (TypeError, KeyError, OverflowError, *_DB_ERRORS):
            _mark_error(response, _format_error("방문 집중 예측 정보를 확인할 수 없어요."))
            response.forecast.status = "unavailable"
            return response
        response.observed_at = forecast_result.observed_at
        upcoming = [day for day in forecast_days if since.date() <= day.date < since.date() + timedelta(days=days)]
        if not forecast_days:
            response.status = "unsupported"
            response.notices.append(_NO_FORECAST)
            return response

        response.forecast = VisitForecast(status="ok", attraction=match.attraction, days=upcoming)
        if since.date() - forecast_days[0].date > timedelta(days=2):
            _stale(response)
            response.forecast.status = "stale"
        return response

    async def _tour_reading(
        self, source: str, target: str, region: str, since: datetime,
        fetch: Callable[[], Awaitable[visit_forecast.TourReading]],
    ) -> visit_forecast.TourReading:
        if os.environ.get("VISIT_FORECAST_STORE", "memory") != "db":
            return await fetch()

        async def load() -> visit_forecast.TourReading:
            reading = await asyncio.to_thread(repository.read_tour_snapshot, source, target, since, self._now())
            if reading is None:
                reading = await fetch()
                await asyncio.to_thread(repository.save_tour_snapshot, source, target, region, reading)
            return reading

        return await self.source.cached(source, f"snapshot:{target}:{since.date().isoformat()}", 86_400, load)


@lru_cache(maxsize=1)
def get_service() -> FestivalInfoService:
    return FestivalInfoService(FestivalSource())
