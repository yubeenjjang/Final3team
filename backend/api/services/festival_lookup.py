from api.mocks.store import festivals
from api.routers.festivals.catalog import uses_festival_db
from api.schemas.festivals import FestivalDetail
from api.services import festival_store


def find_festival(festival_id: str) -> FestivalDetail | None:
    if uses_festival_db():
        return festival_store.get_festival(festival_id)
    return festivals.get(festival_id)
