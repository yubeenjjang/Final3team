from collections import defaultdict
from datetime import datetime, timedelta
from math import cos, floor, isfinite, log, pi, sin, tan
from typing import Any

from api.providers.festival_source import DATA_GO_KR, FestivalSource, FestivalSourceError, public_items
from api.providers.route_base import KST, as_kst
from api.schemas.festival_info import (
    PrecipitationType, RealWeatherForecast, WeatherData, WeatherForecastItem, WeatherGrid,
)

_ENDPOINT = DATA_GO_KR + "/1360000/VilageFcstInfoService_2.0/"
_PRECIPITATION_TYPES: dict[str, PrecipitationType] = {
    "0": "none", "1": "rain", "2": "rain_snow", "3": "snow",
    "5": "drizzle", "6": "drizzle_snow", "7": "snow_flurry",
}
_WEATHER_TTL_S = 600
_FORECAST_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)


def weather_grid(lat: float, lng: float) -> WeatherGrid:
    # 기상청 DFS Lambert conformal conic. 표준 위도 30°/60°, 기준점 38°N 126°E.
    radians = pi / 180
    first, second = 30 * radians, 60 * radians
    cone = log(cos(first) / cos(second)) / log(
        tan(pi / 4 + second / 2) / tan(pi / 4 + first / 2)
    )
    scale = (6371.00877 / 5) * tan(pi / 4 + first / 2) ** cone * cos(first) / cone
    origin = scale / tan(pi / 4 + 38 * radians / 2) ** cone
    radius = scale / tan(pi / 4 + lat * radians / 2) ** cone
    theta = ((lng - 126 + 180) % 360 - 180) * radians * cone
    return WeatherGrid(nx=floor(radius * sin(theta) + 43.5), ny=floor(origin - radius * cos(theta) + 136.5))


def _forecast_release(now: datetime) -> datetime:
    available = now - timedelta(minutes=10)
    for hour in reversed(_FORECAST_HOURS):
        if hour <= available.hour:
            return available.replace(hour=hour, minute=0, second=0, microsecond=0)
    return (available - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)


def _number(value: Any) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError
    return result


def _timestamp(day: Any, hour: Any) -> datetime:
    return datetime.strptime(f"{day}{hour}", "%Y%m%d%H%M").replace(tzinfo=KST)


def _grid_timestamp(row: dict[str, Any], grid: WeatherGrid, now: datetime) -> datetime:
    if (int(row["nx"]), int(row["ny"])) != (grid.nx, grid.ny):
        raise ValueError
    observed_at = _timestamp(row["baseDate"], row["baseTime"])
    if observed_at > now:
        raise ValueError
    return observed_at


def _observations(body: dict[str, Any], grid: WeatherGrid, now: datetime) -> WeatherData:
    rows, total = public_items(body)
    if not rows:
        raise FestivalSourceError("기상청 실황 자료가 없어요.", retryable=False)
    observed_at = _grid_timestamp(rows[0], grid, now)
    if total != len(rows) or any(_grid_timestamp(row, grid, now) != observed_at for row in rows):
        raise ValueError
    values = {row["category"]: row["obsrValue"] for row in rows}
    rain = _number(values["RN1"])
    if rain < 0:
        raise ValueError
    return WeatherData(
        observed_at=observed_at, temperature_c=_number(values["T1H"]),
        precipitation_mm=rain, precipitation_type=_PRECIPITATION_TYPES[str(values["PTY"])],
        grid=grid,
    )


def _precipitation_amount(value: Any) -> float | None:
    text = str(value).strip()
    if text == "강수없음":
        return 0
    if "미만" in text or "이상" in text or "~" in text:
        # 구간 표기는 단일 강수량으로 바꿀 수 없다.
        return None
    amount = _number(text.removesuffix("mm"))
    if amount < 0:
        raise ValueError
    return amount


def _forecast_rows(
    rows: list[dict[str, Any]], grid: WeatherGrid, now: datetime,
) -> tuple[datetime, list[WeatherForecastItem]]:
    if not rows:
        raise FestivalSourceError("기상청 예보 자료가 없어요.", retryable=False)
    issued_at = _grid_timestamp(rows[0], grid, now)
    values: dict[datetime, dict[str, Any]] = defaultdict(dict)
    for row in rows:
        if _grid_timestamp(row, grid, now) != issued_at:
            raise ValueError
        if row["category"] in {"TMP", "PTY", "PCP"}:
            values[_timestamp(row["fcstDate"], row["fcstTime"])][row["category"]] = row["fcstValue"]

    items = [
        WeatherForecastItem(
            forecast_at=forecast_at, temperature_c=_number(fields["TMP"]),
            precipitation_type=_PRECIPITATION_TYPES[str(fields["PTY"])],
            precipitation_mm=_precipitation_amount(fields["PCP"]) if "PCP" in fields else None,
        )
        for forecast_at, fields in sorted(values.items())
        if forecast_at >= issued_at and {"TMP", "PTY"} <= fields.keys()
    ]
    if not items:
        raise ValueError
    return issued_at, items


async def current_weather(client: FestivalSource, grid: WeatherGrid) -> WeatherData:
    now = as_kst(client.now())
    base = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    return await client.cached(
        "kma", f"{grid.nx},{grid.ny}:current", _WEATHER_TTL_S,
        lambda: client.request(
            "kma", _ENDPOINT + "getUltraSrtNcst", lambda body: _observations(body, grid, now),
            params=_parameters(grid, base, 10, 1),
        ),
    )


async def short_forecast(client: FestivalSource, grid: WeatherGrid) -> RealWeatherForecast:
    now = as_kst(client.now())
    base = _forecast_release(now)

    async def load() -> tuple[datetime, list[WeatherForecastItem]]:
        rows: list[dict[str, Any]] = []
        for page in range(1, 5):
            batch, total = await client.request(
                "kma", _ENDPOINT + "getVilageFcst", public_items,
                params=_parameters(grid, base, 1000, page),
            )
            rows.extend(batch)
            if len(rows) >= total:
                break
        else:
            raise FestivalSourceError("기상청 예보 페이지를 모두 확인할 수 없어요.", retryable=False)
        try:
            return _forecast_rows(rows, grid, now)
        except (ValueError, TypeError, KeyError, OverflowError):
            raise FestivalSourceError(retryable=False) from None

    issued_at, items = await client.cached("kma", f"{grid.nx},{grid.ny}:forecast", _WEATHER_TTL_S, load)
    now = as_kst(client.now())
    upcoming = [item for item in items if item.forecast_at >= now.replace(minute=0, second=0, microsecond=0)]
    if not upcoming:
        raise FestivalSourceError("현재 시점의 기상청 예보 자료가 없어요.", retryable=False)
    return RealWeatherForecast(
        status="stale" if now - issued_at > timedelta(hours=6) else "ok",
        issued_at=issued_at, items=upcoming,
    )


def _parameters(grid: WeatherGrid, base: datetime, rows: int, page: int) -> dict[str, str | int]:
    return {
        "dataType": "JSON", "pageNo": page, "numOfRows": rows,
        "base_date": base.strftime("%Y%m%d"), "base_time": base.strftime("%H%M"),
        "nx": grid.nx, "ny": grid.ny,
    }
