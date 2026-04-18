import pytest

from app.models import Metadata, Resource
from app.schemas import WallpaperQueryParams
from app.services import wallpaper_service, filter_service, health_service


def _insert_wallpaper(session, suffix, mkt="zh-CN", year=2026, month=4):
    sha = f"{'a' * 60}{suffix:04d}"
    resource = Resource(
        sha256=sha,
        year=year,
        month=month,
        base_path=f"wallpaper/{year}/{month:02d}/{sha}",
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=1000000,
    )
    session.add(resource)
    meta = Metadata(
        mkt=mkt,
        date=f"{year}-{month:02d}-{suffix:02d}",
        sha256=sha,
        hsh=f"hsh_{suffix}",
        title=f"Title {suffix}",
        copyright=f"Copyright {suffix}",
    )
    session.add(meta)
    session.commit()
    return resource, meta


def test_empty_list(db_session):
    params = WallpaperQueryParams()
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 0
    assert result.items == []


def test_list_with_data(db_session):
    _insert_wallpaper(db_session, 1)
    _insert_wallpaper(db_session, 2)
    params = WallpaperQueryParams()
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 2


def test_filter_by_mkt(db_session):
    _insert_wallpaper(db_session, 1, mkt="zh-CN")
    _insert_wallpaper(db_session, 2, mkt="en-US")
    params = WallpaperQueryParams(mkt="zh-CN")
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 1
    assert result.items[0].mkt == "zh-CN"


def test_filter_by_year(db_session):
    _insert_wallpaper(db_session, 1, year=2026)
    _insert_wallpaper(db_session, 2, year=2025)
    params = WallpaperQueryParams(year=2026)
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 1


def test_keyword_requires_filter(db_session):
    params = WallpaperQueryParams(keyword="test")
    with pytest.raises(ValueError, match="keyword requires"):
        wallpaper_service.list_wallpapers(db_session, params)


def test_keyword_with_mkt(db_session):
    _insert_wallpaper(db_session, 1)
    params = WallpaperQueryParams(mkt="zh-CN", keyword="Title")
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 1


def test_pagination(db_session):
    for i in range(25):
        _insert_wallpaper(db_session, i + 1)
    params = WallpaperQueryParams(page=1, size=10)
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 25
    assert len(result.items) == 10
    assert result.pages == 3


def test_soft_delete_excluded(db_session):
    res, meta = _insert_wallpaper(db_session, 1)
    meta.is_deleted = 1
    db_session.commit()
    params = WallpaperQueryParams()
    result = wallpaper_service.list_wallpapers(db_session, params)
    assert result.total == 0


def test_filter_options(db_session):
    filter_service._cache.clear()
    _insert_wallpaper(db_session, 1, mkt="zh-CN", year=2026, month=4)
    _insert_wallpaper(db_session, 2, mkt="en-US", year=2026, month=3)
    result = filter_service.get_filter_options(db_session)
    assert "zh-CN" in result.markets
    assert "en-US" in result.markets
    assert 2026 in result.years
    filter_service._cache.clear()


def test_health(db_session):
    result = health_service.get_health(db_session)
    assert result.db_ok is True
    assert result.status == "healthy"
