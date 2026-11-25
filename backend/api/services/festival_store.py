from datetime import date, datetime

from sqlalchemy import RowMapping, case, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from api.ingestion.festivals.normalize import FESTIVAL_CATEGORY, FESTIVAL_CLASS, KST
from api.ingestion.festivals.store import FESTIVAL_SOURCES, FESTIVALS, SOURCE_ID
from api.schemas.festivals import FestivalDetail, FestivalListItem, FestivalPage, FestivalQuery
from api.services.admin_festivals import ADMIN_IMAGE_CREDIT, ADMIN_SOURCE_ID
from shared.db.session import user_db_session

_F = FESTIVALS.c
_SOURCE = FESTIVAL_SOURCES.c
_PUBLIC = (
    _F.category == FESTIVAL_CATEGORY, _F.source_class_level2 == FESTIVAL_CLASS,
    _F.review_status == "approved", _F.published_at.is_not(None),
)
_IMAGE_CREDIT = "한국관광공사"
_SORT_ORDERS = {
    "start_date": _F.start_date.asc().nulls_last(),
    "-start_date": _F.start_date.desc().nulls_last(),
    "name": _F.title.asc(),
}
_SOURCE_REF = (
    select(_SOURCE.source_item_id)
    .where(_SOURCE.festival_id == _F.festival_id, _SOURCE.source_id == SOURCE_ID)
    .order_by(_SOURCE.source_item_id)
    .limit(1)
    .scalar_subquery()
    .label("source_ref")
)
_IS_ADMIN_SOURCE = (
    select(_SOURCE.festival_id)
    .where(_SOURCE.festival_id == _F.festival_id, _SOURCE.source_id == ADMIN_SOURCE_ID,
           _SOURCE.source_item_id == _F.festival_id)
    .exists()
    .label("is_admin_source")
)


def _event_status(today: date) -> ColumnElement[str]:
    return case(
        (_F.event_status == "cancelled", "cancelled"),
        (or_(_F.start_date.is_(None), _F.end_date.is_(None)), "needs_review"),
        (_F.start_date > today, "upcoming"),
        (_F.end_date < today, "ended"),
        else_="ongoing",
    )


def _list_columns(status: ColumnElement[str]) -> tuple[ColumnElement, ...]:
    return (
        _F.festival_id, _F.title.label("name"), _F.region_code, _F.venue_name,
        _F.latitude.label("lat"), _F.longitude.label("lng"), _F.start_date,
        _F.end_date, status.label("event_status"), _F.thumbnail_url, _F.image_url,
        _F.last_synced_at, _IS_ADMIN_SOURCE,
    )


def _filters(query: FestivalQuery, status: ColumnElement[str]) -> list[ColumnElement[bool]]:
    filters = list(_PUBLIC)
    if query.region != "ALL":
        filters.append(_F.region_code == query.region)
    if query.statuses:
        filters.append(status.in_(query.statuses))
    if query.q is not None:
        term = query.q.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        pattern = f"%{term}%"
        filters.append(or_(
            _F.title.ilike(pattern, escape="!"),
            _F.venue_name.ilike(pattern, escape="!"),
        ))
    if query.date_from is not None or query.date_to is not None:
        filters.extend((_F.start_date.is_not(None), _F.end_date.is_not(None)))
    if query.date_from is not None:
        filters.append(_F.end_date >= query.date_from)
    if query.date_to is not None:
        filters.append(_F.start_date <= query.date_to)
    return filters


def _response_values(row: RowMapping) -> dict[str, object]:
    values = dict(row)
    credit = ADMIN_IMAGE_CREDIT if row.is_admin_source else _IMAGE_CREDIT
    values["source"] = "admin" if row.is_admin_source else "tourapi"
    values["image_credit"] = credit if row.image_url or row.thumbnail_url else None
    synced_at = row.last_synced_at
    values["last_synced_at"] = synced_at.astimezone(KST).isoformat() if synced_at else ""
    return values


async def list_festivals(query: FestivalQuery) -> FestivalPage:
    async with user_db_session(user_id=None) as db:
        # Set isolation before the session checks out a connection or runs its first query.
        await db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        status = _event_status(datetime.now(KST).date())
        filters = _filters(query, status)
        count = await db.execute(
            select(func.count()).select_from(FESTIVALS).where(*filters)
        )
        total = count.scalar_one()
        offset = (query.page - 1) * query.page_size
        items: list[FestivalListItem] = []
        if offset < total:
            page = await db.execute(
                select(*_list_columns(status))
                .where(*filters)
                .order_by(_SORT_ORDERS[query.sort], _F.festival_id)
                .offset(offset)
                .limit(query.page_size)
            )
            items = [FestivalListItem.model_validate(_response_values(row)) for row in page.mappings()]
    return FestivalPage(items=items, total=total, page=query.page, page_size=query.page_size, is_mock=False)


async def get_festival(festival_id: str) -> FestivalDetail | None:
    async with user_db_session(user_id=None) as db:
        status = _event_status(datetime.now(KST).date())
        result = await db.execute(
            select(
                *_list_columns(status), _F.address, _F.summary.label("overview"),
                _F.admission_fee_text.label("fee_text"), _F.official_url.label("homepage_url"),
                _F.image_copyright_type, _SOURCE_REF,
            ).where(*_PUBLIC, _F.festival_id == festival_id)
        )
        row = result.mappings().one_or_none()
    if row is None:
        return None

    values = _response_values(row)
    values["overview"] = row.overview or ""
    values["source_ref"] = row.festival_id if row.is_admin_source else row.source_ref or ""
    values["is_mock"] = False
    values["image_copyright"] = (
        {"type": row.image_copyright_type, "credit": values["image_credit"],
         "modify_allowed": row.image_copyright_type == "Type1"}
        if values["image_credit"] and row.image_copyright_type
        else None
    )
    return FestivalDetail.model_validate(values)
