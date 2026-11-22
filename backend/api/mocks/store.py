from api.mocks.festivals import FESTIVALS
from api.schemas.festivals import FestivalDetail

festivals: dict[str, FestivalDetail] = {}


def reset_store() -> None:
    festivals.clear()
    festivals.update(
        (festival.festival_id, festival.model_copy(deep=True)) for festival in FESTIVALS
    )


reset_store()
