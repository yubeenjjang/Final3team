from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.errors import ApiError
from api.schemas.favorites import FavoritesPage, FavoritesQuery, FavoriteSave

_PUBLIC_FESTIVAL = "f.category = 'festival' AND f.review_status = 'approved' AND f.published_at IS NOT NULL"


async def list_favorites(db: AsyncSession, query: FavoritesQuery) -> FavoritesPage:
    order = "saved_at DESC, festival_id ASC"
    if query.sort == "start_date":
        order = f"start_date ASC NULLS LAST, {order}"
    # Count and page use the same snapshot, including when the requested page is empty.
    rows = (await db.execute(text(f"""
        WITH visible AS (
            SELECT f.festival_id, f.title AS name, f.region_code, f.start_date, f.end_date,
                   f.event_status, f.thumbnail_url, fav.created_at AS saved_at
            FROM public.favorites fav JOIN public.festivals f USING (festival_id)
            WHERE fav.user_id = public.app_current_user() AND {_PUBLIC_FESTIVAL}
        )
        SELECT page.*, totals.total
        FROM (SELECT count(*) AS total FROM visible) totals
        LEFT JOIN LATERAL (
            SELECT * FROM visible ORDER BY {order} LIMIT :limit OFFSET :offset
        ) page ON true
        ORDER BY {order}
    """), {"limit": query.page_size, "offset": min((query.page - 1) * query.page_size, 2**63 - 1)})).mappings().all()
    return FavoritesPage(
        items=[dict(row) for row in rows if row["festival_id"] is not None],
        total=rows[0]["total"], page=query.page, page_size=query.page_size, is_mock=False,
    )


async def save_favorite(db: AsyncSession, festival_id: str) -> tuple[FavoriteSave, bool]:
    params = {"festival_id": festival_id}
    saved_at = await db.scalar(text(f"""
        INSERT INTO public.favorites (user_id, festival_id)
        SELECT public.app_current_user(), f.festival_id FROM public.festivals f
        WHERE f.festival_id = :festival_id AND {_PUBLIC_FESTIVAL}
        ON CONFLICT (user_id, festival_id) DO NOTHING
        RETURNING created_at
    """), params)
    created = saved_at is not None
    if not created:
        saved_at = await db.scalar(text(f"""
            SELECT fav.created_at FROM public.favorites fav JOIN public.festivals f USING (festival_id)
            WHERE fav.user_id = public.app_current_user() AND f.festival_id = :festival_id
              AND {_PUBLIC_FESTIVAL}
        """), params)
        if saved_at is None:
            raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
    return FavoriteSave(festival_id=festival_id, saved_at=saved_at, is_mock=False), created


async def delete_favorite(db: AsyncSession, festival_id: str) -> None:
    await db.execute(text("""
        DELETE FROM public.favorites
        WHERE user_id = public.app_current_user() AND festival_id = :festival_id
    """), {"festival_id": festival_id})
