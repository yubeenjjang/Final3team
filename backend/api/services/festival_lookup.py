from api.mocks.store import get_public_mock_festival
from api.routers.festivals.catalog import uses_festival_db
from api.schemas.festivals import FestivalDetail
from api.services import festival_store


async def find_festival(festival_id: str) -> FestivalDetail | None:
    if uses_festival_db():
        return await festival_store.get_festival(festival_id)
    return get_public_mock_festival(festival_id)
