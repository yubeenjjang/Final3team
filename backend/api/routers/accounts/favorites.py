from typing import Annotated

from fastapi import APIRouter, Header, Path, Query, Response

from api.schemas.favorites import FavoriteSave, FavoritesPage, FavoritesQuery
from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.services import mock_favorites

router = APIRouter(prefix="/me/favorites")
Authorization = Annotated[str | None, Header()]
FestivalId = Annotated[str, Path(pattern=FESTIVAL_ID_PATTERN)]


@router.get("")
def list_favorites(
    query: Annotated[FavoritesQuery, Query()], authorization: Authorization = None
) -> FavoritesPage:
    return mock_favorites.list_favorites(authorization, query)


@router.put(
    "/{festival_id}", status_code=201, responses={200: {"model": FavoriteSave}}
)
def save_favorite(
    festival_id: FestivalId, response: Response, authorization: Authorization = None
) -> FavoriteSave:
    favorite, created = mock_favorites.save_favorite(authorization, festival_id)
    if not created:
        response.status_code = 200
    return favorite


@router.delete("/{festival_id}", status_code=204)
def delete_favorite(festival_id: FestivalId, authorization: Authorization = None) -> Response:
    mock_favorites.delete_favorite(authorization, festival_id)
    return Response(status_code=204)
