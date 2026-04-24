from datetime import date as date_type
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int
    msg: str
    data: Optional[T] = None


class WallpaperQueryParams(BaseModel):
    mkt: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    date: Optional[date_type] = None
    date_from: Optional[date_type] = None
    date_to: Optional[date_type] = None
    keyword: Optional[str] = Field(default=None, min_length=2)
    dedup: bool = False
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class WallpaperItem(BaseModel):
    id: str
    mkt: str | list[str]
    date: str
    title: Optional[str] = None
    copyright: Optional[str] = None
    copyrightlink: Optional[str] = None
    width: int
    height: int
    bytes: int
    ext: str
    mime_type: str
    thumbnail_url: str
    preview_url: str
    download_url: str


class WallpaperListResponse(BaseModel):
    items: list[WallpaperItem]
    total: int
    page: int
    size: int
    pages: int


class RandomWallpaperResponse(BaseModel):
    id: str
    title: Optional[str] = None
    copyright: Optional[str] = None
    copyrightlink: Optional[str] = None
    width: int
    height: int
    image_url: str


class FilterOptions(BaseModel):
    markets: list[str]
    years: list[int]
    year_months: dict[int, list[int]]


class HealthResponse(BaseModel):
    status: str
    db_ok: bool
    last_success_at: Optional[str] = None
    wallpaper_count: int
    resource_count: int
    markets_count: int
