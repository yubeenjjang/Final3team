from dataclasses import dataclass
from threading import Lock

from api.mocks.festivals import FESTIVALS
from api.schemas.festivals import FestivalDetail
from api.schemas.routes import RouteDirection, RouteRequest, RouteStatus


@dataclass
class RouteRecord:
    route_request_id: str
    access_token: str
    direction: RouteDirection
    request: RouteRequest
    festival: FestivalDetail
    body: str
    scenario: str
    status: RouteStatus
    updated_at: str


festivals: dict[str, FestivalDetail] = {}
route_requests: dict[str, RouteRecord] = {}
route_request_keys: dict[tuple[RouteDirection, str], str] = {}
route_lock = Lock()


def reset_store() -> None:
    with route_lock:
        festivals.clear()
        festivals.update(
            (festival.festival_id, festival.model_copy(deep=True)) for festival in FESTIVALS
        )
        route_requests.clear()
        route_request_keys.clear()


reset_store()
