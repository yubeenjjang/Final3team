import os
from datetime import date, datetime
from functools import lru_cache

from sqlalchemy import URL, Engine, RowMapping, case, create_engine, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from api.ingestion.festivals.normalize import KST
from api.ingestion.festivals.store import FESTIVAL_SOURCES, FESTIVALS, SOURCE_ID
from api.schemas.festivals import FestivalDetail, FestivalListItem, FestivalPage, FestivalQuery

_F = FESTIVALS.c
_SOURCE = FESTIVAL_SOURCES.c
_PUBLIC = (_F.review_status == "approved", _F.published_at.is_not(None))
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


def get_festival_engine() -> Engine:
    password = os.environ.get("DB_USER_PASSWORD")
    if not password:
        raise RuntimeError("DB_USER_PASSWORD를 설정해 주세요.")
    try:
        port = int(os.environ.get("DB_PORT", "5432"))
    except ValueError:
        raise RuntimeError("DB_PORT는 숫자여야 합니다.") from None
    if not 1 <= port <= 65535:
        raise RuntimeError("DB_PORT는 1부터 65535 사이여야 합니다.")
    return _create_engine(URL.create(
        "postgresql+psycopg",
        username=os.environ.get("DB_USER_USERNAME", "noldaga_app"),
        password=password,
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=port,
        database=os.environ.get("DB_NAME", "noldaga"),
    ))


@lru_cache(maxsize=1)
def _create_engine(url: URL) -> Engine:
    return create_engine(url, hide_parameters=True, isolation_level="REPEATABLE READ")


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
        _F.last_synced_at,
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
    values["image_credit"] = _IMAGE_CREDIT if row.image_url or row.thumbnail_url else None
    synced_at = row.last_synced_at
    values["last_synced_at"] = synced_at.astimezone(KST).isoformat() if synced_at else ""
    return values


def list_festivals(query: FestivalQuery) -> FestivalPage:
    with get_festival_engine().begin() as connection:
        status = _event_status(datetime.now(KST).date())
        filters = _filters(query, status)
        total = connection.execute(
            select(func.count()).select_from(FESTIVALS).where(*filters)
        ).scalar_one()
        offset = (query.page - 1) * query.page_size
        items: list[FestivalListItem] = []
        if offset < total:
            rows = connection.execute(
                select(*_list_columns(status))
                .where(*filters)
                .order_by(_SORT_ORDERS[query.sort], _F.festival_id)
                .offset(offset)
                .limit(query.page_size)
            ).mappings()
            items = [FestivalListItem.model_validate(_response_values(row)) for row in rows]
    return FestivalPage(items=items, total=total, page=query.page, page_size=query.page_size, is_mock=False)


def get_festival(festival_id: str) -> FestivalDetail | None:
    with get_festival_engine().begin() as connection:
        status = _event_status(datetime.now(KST).date())
        row = connection.execute(
            select(
                *_list_columns(status), _F.address, _F.summary.label("overview"),
                _F.admission_fee_text.label("fee_text"), _F.official_url.label("homepage_url"),
                _F.image_copyright_type, _SOURCE_REF,
            ).where(*_PUBLIC, _F.festival_id == festival_id)
        ).mappings().one_or_none()
    if row is None:
        return None

    values = _response_values(row)
    values["overview"] = row.overview or ""
    values["source_ref"] = row.source_ref or ""
    values["is_mock"] = False
    values["image_copyright"] = (
        {"type": row.image_copyright_type, "credit": _IMAGE_CREDIT,
         "modify_allowed": row.image_copyright_type == "Type1"}
        if values["image_credit"] and row.image_copyright_type
        else None
    )
    return FestivalDetail.model_validate(values)
