from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from api.schemas.festivals import FestivalStatus, RegionCode


class FavoritesQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort: Literal["-saved_at", "start_date"] = "-saved_at"


class FavoriteResponse(BaseModel):
    is_mock: bool = True


class FavoriteSave(FavoriteResponse):
    festival_id: str
    saved_at: datetime


class FavoriteItem(BaseModel):
    festival_id: str
    name: str
    region_code: RegionCode
    start_date: date | None
    end_date: date | None
    event_status: FestivalStatus
    thumbnail_url: str | None
    saved_at: datetime


class FavoritesPage(FavoriteResponse):
    items: list[FavoriteItem]
    total: int
    page: int
    page_size: int
