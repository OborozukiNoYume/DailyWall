import pytest

from app.models import Metadata, Resource
from app.schemas import WallpaperQueryParams
from app.services import wallpaper_service, filter_service, health_service


def _insert_wallpaper(
    session,
    suffix,
    mkt="zh-CN",
    year=2026,
    month=4,
    sha=None,
    date=None,
    title=None,
    copyright=None,
):
    sha = sha or f"{'a' * 60}{suffix:04d}"
    resource = session.get(Resource, sha)
    if resource is None:
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
        date=date or f"{year}-{month:02d}-{suffix:02d}",
        sha256=sha,
        hsh=f"hsh_{suffix}",
        title=title or f"Title {suffix}",
        copyright=copyright or f"Copyright {suffix}",
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


def test_dedup_groups_by_sha_and_uses_priority_metadata(db_session):
    sha = "c" * 64
    _insert_wallpaper(
        db_session,
        1,
        mkt="en-US",
        sha=sha,
        date="2026-04-19",
        title="English Title",
        copyright="English Copyright",
    )
    _insert_wallpaper(
        db_session,
        2,
        mkt="zh-CN",
        sha=sha,
        date="2026-04-18",
        title="中文标题",
        copyright="中文版权",
    )

    params = WallpaperQueryParams(dedup=True)
    result = wallpaper_service.list_wallpapers(db_session, params)

    assert result.total == 1
    assert len(result.items) == 1
    assert result.items[0].mkt == ["zh-CN", "en-US"]
    assert result.items[0].date == "2026-04-18"
    assert result.items[0].title == "中文标题"
    assert result.items[0].copyright == "中文版权"


def test_dedup_keyword_matches_any_metadata(db_session):
    sha = "d" * 64
    _insert_wallpaper(
        db_session,
        1,
        mkt="zh-CN",
        sha=sha,
        date="2026-04-18",
        title="普通标题",
    )
    _insert_wallpaper(
        db_session,
        2,
        mkt="en-US",
        sha=sha,
        date="2026-04-19",
        title="Aurora Over Lake",
    )

    params = WallpaperQueryParams(year=2026, keyword="Aurora", dedup=True)
    result = wallpaper_service.list_wallpapers(db_session, params)

    assert result.total == 1
    assert result.items[0].id == sha
    assert result.items[0].mkt == ["zh-CN", "en-US"]


def test_dedup_mkt_filter_returns_all_markets_for_matched_image(db_session):
    sha = "e" * 64
    _insert_wallpaper(db_session, 1, mkt="zh-CN", sha=sha, date="2026-04-18")
    _insert_wallpaper(db_session, 2, mkt="en-US", sha=sha, date="2026-04-19")

    params = WallpaperQueryParams(mkt="zh-CN", dedup=True)
    result = wallpaper_service.list_wallpapers(db_session, params)

    assert result.total == 1
    assert result.items[0].mkt == ["zh-CN", "en-US"]


def test_dedup_pagination_counts_unique_resources(db_session):
    shared_sha = "f" * 64
    _insert_wallpaper(db_session, 1, mkt="zh-CN", sha=shared_sha)
    _insert_wallpaper(db_session, 2, mkt="en-US", sha=shared_sha)
    _insert_wallpaper(db_session, 3, mkt="ja-JP")

    params = WallpaperQueryParams(dedup=True, page=1, size=1)
    result = wallpaper_service.list_wallpapers(db_session, params)

    assert result.total == 2
    assert result.pages == 2
    assert len(result.items) == 1


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
