from datetime import date, datetime, timezone

from api.errors import ApiError
from api.mocks.store import (
    FavoriteRecord,
    auth_lock,
    favorite_sequence,
    favorites_by_user,
)
from api.schemas.favorites import FavoriteItem, FavoriteSave, FavoritesPage, FavoritesQuery
from api.services.festival_lookup import find_festival
from api.services.mock_auth import authenticated_access


def _user_id(authorization: str | None, now: datetime) -> str:
    _, session = authenticated_access(authorization, now)
    return session.user_id


async def save_favorite(authorization: str | None, festival_id: str) -> tuple[FavoriteSave, bool]:
    with auth_lock:
        _user_id(authorization, datetime.now(timezone.utc))
    festival = await find_festival(festival_id)
    with auth_lock:
        now = datetime.now(timezone.utc)
        user_id = _user_id(authorization, now)
        if festival is None:
            raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
        saved = favorites_by_user.setdefault(user_id, {})
        record = saved.get(festival_id)
        created = record is None
        if record is None:
            record = FavoriteRecord(now.replace(microsecond=0), next(favorite_sequence))
            saved[festival_id] = record
        return FavoriteSave(festival_id=festival_id, saved_at=record.saved_at), created


def delete_favorite(authorization: str | None, festival_id: str) -> None:
    with auth_lock:
        user_id = _user_id(authorization, datetime.now(timezone.utc))
        saved = favorites_by_user.get(user_id)
        if saved is not None:
            saved.pop(festival_id, None)


async def list_favorites(authorization: str | None, query: FavoritesQuery) -> FavoritesPage:
    with auth_lock:
        user_id = _user_id(authorization, datetime.now(timezone.utc))
        saved = tuple(favorites_by_user.get(user_id, {}).items())
    entries = [
        (festival, record)
        for festival_id, record in saved
        if (festival := await find_festival(festival_id)) is not None
    ]

    entries.sort(key=lambda entry: entry[1].sequence, reverse=True)
    if query.sort == "start_date":
        entries.sort(key=lambda entry: (entry[0].start_date is None, entry[0].start_date or date.max))

    offset = (query.page - 1) * query.page_size
    items = [
        FavoriteItem(
            festival_id=festival.festival_id,
            name=festival.name,
            region_code=festival.region_code,
            start_date=festival.start_date,
            end_date=festival.end_date,
            event_status=festival.event_status,
            thumbnail_url=festival.thumbnail_url,
            saved_at=record.saved_at,
        )
        for festival, record in entries[offset : offset + query.page_size]
    ]
    return FavoritesPage(items=items, total=len(entries), page=query.page, page_size=query.page_size)
