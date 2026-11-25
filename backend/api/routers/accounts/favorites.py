from typing import Annotated

from fastapi import APIRouter, Path, Query, Response
from starlette.concurrency import run_in_threadpool

from api.deps import Authorization
from api.repositories import favorites as repository
from api.routers.accounts.dependencies import MeSession
from api.schemas.favorites import FavoriteSave, FavoritesPage, FavoritesQuery
from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.services import mock_favorites

router = APIRouter(prefix="/me/favorites")
FestivalId = Annotated[str, Path(pattern=FESTIVAL_ID_PATTERN)]


@router.get("")
async def list_favorites(
    query: Annotated[FavoritesQuery, Query()], auth: MeSession, authorization: Authorization = None,
) -> FavoritesPage:
    if auth is None:
        return await mock_favorites.list_favorites(authorization, query)
    return await repository.list_favorites(auth[1], query)


@router.put(
    "/{festival_id}", status_code=201, responses={200: {"model": FavoriteSave}}
)
async def save_favorite(
    festival_id: FestivalId, response: Response, auth: MeSession, authorization: Authorization = None,
) -> FavoriteSave:
    if auth is None:
        favorite, created = await mock_favorites.save_favorite(authorization, festival_id)
    else:
        favorite, created = await repository.save_favorite(auth[1], festival_id)
    if not created:
        response.status_code = 200
    return favorite


@router.delete("/{festival_id}", status_code=204)
async def delete_favorite(festival_id: FestivalId, auth: MeSession, authorization: Authorization = None) -> Response:
    if auth is None:
        await run_in_threadpool(mock_favorites.delete_favorite, authorization, festival_id)
    else:
        await repository.delete_favorite(auth[1], festival_id)
    return Response(status_code=204)
