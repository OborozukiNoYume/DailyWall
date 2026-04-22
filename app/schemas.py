from typing import Optional

from pydantic import BaseModel, Field


class WallpaperQueryParams(BaseModel):
    mkt: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
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
