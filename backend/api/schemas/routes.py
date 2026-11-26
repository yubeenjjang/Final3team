from typing import Literal, Self

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from api.schemas.festivals import FESTIVAL_ID_PATTERN

ROUTE_REQUEST_ID_PATTERN = r"^rr_[0-9A-Za-z]{6,26}$"
RouteDirection = Literal["return", "visit"]
RouteStatus = Literal["queued", "processing", "ready", "unavailable", "timed_out", "rejected"]
RoutePreference = Literal["fastest", "less_crowded", "accessible", "min_walk", "fewest_transfers"]


class Place(BaseModel):
    query: str | None = Field(default=None, min_length=1, max_length=100)
    lat: float | None = Field(default=None, ge=33.0, le=39.0)
    lng: float | None = Field(default=None, ge=124.0, le=132.0)

    @model_validator(mode="after")
    def validate_place(self) -> Self:
        if self.query is not None and self.lat is None and self.lng is None:
            return self
        if self.query is None and self.lat is not None and self.lng is not None:
            return self
        raise ValueError("장소 검색어 또는 위도와 경도를 입력해 주세요.")


class FestivalEndpoint(BaseModel):
    type: Literal["festival"]


class PlaceEndpoint(Place):
    type: Literal["place"] = "place"


Endpoint = FestivalEndpoint | PlaceEndpoint


class UserConstraints(BaseModel):
    with_child: bool = False
    wheelchair: bool = False
    max_walk_m: int | None = Field(default=None, ge=0, le=5000)


class RouteRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    festival_id: str = Field(pattern=FESTIVAL_ID_PATTERN)
    origin: Endpoint
    destination: Endpoint
    travel_mode: Literal["transit", "walk", "car", "taxi"] = "transit"
    route_preference: RoutePreference = "fastest"
    user_constraints: UserConstraints = Field(default_factory=UserConstraints)
    departure: Literal["now"] = "now"

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, destination: Endpoint, info: ValidationInfo) -> Endpoint:
        if isinstance(destination, FestivalEndpoint) and isinstance(
            info.data.get("origin"), FestivalEndpoint
        ):
            raise ValueError("출발지와 도착지를 모두 축제 장소로 지정할 수 없습니다.")
        return destination


def _festival_endpoint() -> FestivalEndpoint:
    return FestivalEndpoint(type="festival")


class ReturnRouteRequest(RouteRequest):
    origin: Endpoint = Field(default_factory=_festival_endpoint)


class VisitRouteRequest(RouteRequest):
    destination: Endpoint = Field(default_factory=_festival_endpoint, validate_default=True)
