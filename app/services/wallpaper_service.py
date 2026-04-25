import math
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.models import Metadata, Resource
from app.schemas import (
    RandomWallpaperResponse,
    WallpaperItem,
    WallpaperListResponse,
    WallpaperQueryParams,
)

MARKET_PRIORITY = {"zh-CN": 0, "en-US": 1}


def _market_sort_key(mkt: str) -> tuple[int, str]:
    return (MARKET_PRIORITY.get(mkt, 2), mkt)


def _metadata_priority(meta: Metadata) -> tuple[int, int, int, str, str]:
    return (
        MARKET_PRIORITY.get(meta.mkt, 2),
        0 if meta.title else 1,
        0 if meta.copyright else 1,
        meta.date,
        meta.mkt,
    )


def _build_filtered_query(session: Session, params: WallpaperQueryParams):
    query = (
        session.query(Metadata, Resource)
        .join(Resource, Metadata.sha256 == Resource.sha256)
        .filter(Metadata.is_deleted == 0, Resource.is_deleted == 0)
    )

    if params.mkt:
        query = query.filter(Metadata.mkt == params.mkt)
    if params.year:
        query = query.filter(Resource.year == params.year)
    if params.month:
        query = query.filter(Resource.month == params.month)
    if params.date:
        query = query.filter(Metadata.date == params.date.isoformat())
    if params.date_from:
        query = query.filter(Metadata.date >= params.date_from.isoformat())
    if params.date_to:
        query = query.filter(Metadata.date <= params.date_to.isoformat())
    if params.keyword:
        keyword = f"%{params.keyword}%"
        query = query.filter(
            or_(
                Metadata.title.ilike(keyword),
                Metadata.copyright.ilike(keyword),
            )
        )

    return query


def _list_wallpapers_default(
    session: Session, params: WallpaperQueryParams
) -> WallpaperListResponse:
    base_query = _build_filtered_query(session, params)

    total = base_query.count()
    pages = math.ceil(total / params.size) if total > 0 else 0

    rows = (
        base_query.order_by(Metadata.date.desc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
        .all()
    )

    items = []
    for meta, res in rows:
        items.append(
            WallpaperItem(
                id=res.sha256,
                mkt=meta.mkt,
                date=meta.date,
                title=meta.title,
                copyright=meta.copyright,
                copyrightlink=meta.copyrightlink,
                width=res.width,
                height=res.height,
                bytes=res.bytes,
                ext=res.ext,
                mime_type=res.mime_type,
                thumbnail_url=f"/api/images/{res.sha256}?size=thumbnail",
                preview_url=f"/api/images/{res.sha256}?size=preview",
                download_url=f"/api/images/{res.sha256}/download",
            )
        )

    return WallpaperListResponse(
        items=items,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


def _list_wallpapers_dedup(
    session: Session, params: WallpaperQueryParams
) -> WallpaperListResponse:
    matching_shas = (
        _build_filtered_query(session, params)
        .with_entities(Resource.sha256.label("sha256"))
        .distinct()
        .subquery()
    )

    total = session.query(func.count()).select_from(matching_shas).scalar() or 0
    pages = math.ceil(total / params.size) if total > 0 else 0

    if total == 0:
        return WallpaperListResponse(
            items=[],
            total=0,
            page=params.page,
            size=params.size,
            pages=0,
        )

    display_date = func.coalesce(
        func.min(case((Metadata.mkt == "zh-CN", Metadata.date), else_=None)),
        func.min(Metadata.date),
    )

    rows = (
        session.query(
            Resource.sha256.label("sha256"),
            display_date.label("date"),
            Resource.width.label("width"),
            Resource.height.label("height"),
            Resource.bytes.label("bytes"),
            Resource.ext.label("ext"),
            Resource.mime_type.label("mime_type"),
        )
        .join(matching_shas, matching_shas.c.sha256 == Resource.sha256)
        .join(Metadata, Metadata.sha256 == Resource.sha256)
        .filter(Metadata.is_deleted == 0, Resource.is_deleted == 0)
        .group_by(
            Resource.sha256,
            Resource.width,
            Resource.height,
            Resource.bytes,
            Resource.ext,
            Resource.mime_type,
        )
        .order_by(display_date.desc(), Resource.sha256.desc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
        .all()
    )

    page_shas = [row.sha256 for row in rows]
    if not page_shas:
        return WallpaperListResponse(
            items=[],
            total=total,
            page=params.page,
            size=params.size,
            pages=pages,
        )

    metadata_rows = (
        session.query(Metadata)
        .filter(Metadata.is_deleted == 0, Metadata.sha256.in_(page_shas))
        .order_by(Metadata.date.asc(), Metadata.mkt.asc())
        .all()
    )

    metadata_by_sha = defaultdict(list)
    for meta in metadata_rows:
        metadata_by_sha[meta.sha256].append(meta)

    items = []
    for row in rows:
        entries = metadata_by_sha[row.sha256]
        preferred = min(entries, key=_metadata_priority)
        mkts = sorted({meta.mkt for meta in entries}, key=_market_sort_key)

        items.append(
            WallpaperItem(
                id=row.sha256,
                mkt=mkts,
                date=row.date,
                title=preferred.title,
                copyright=preferred.copyright,
                copyrightlink=preferred.copyrightlink,
                width=row.width,
                height=row.height,
                bytes=row.bytes,
                ext=row.ext,
                mime_type=row.mime_type,
                thumbnail_url=f"/api/images/{row.sha256}?size=thumbnail",
                preview_url=f"/api/images/{row.sha256}?size=preview",
                download_url=f"/api/images/{row.sha256}/download",
            )
        )

    return WallpaperListResponse(
        items=items,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )


def list_wallpapers(
    session: Session, params: WallpaperQueryParams
) -> WallpaperListResponse:
    if params.date and (params.date_from or params.date_to):
        raise ValueError("date 不能与 date_from 或 date_to 同时使用")

    if params.date_from and params.date_to and params.date_from > params.date_to:
        raise ValueError("date_from 不能晚于 date_to")

    if params.keyword and not any(
        [
            params.mkt,
            params.year,
            params.month,
            params.date,
            params.date_from,
            params.date_to,
        ]
    ):
        raise ValueError("keyword 必须搭配 mkt、year、month、date、date_from、date_to 之一")

    if params.dedup:
        return _list_wallpapers_dedup(session, params)

    return _list_wallpapers_default(session, params)


def get_random_wallpaper(session: Session) -> RandomWallpaperResponse:
    resource = (
        session.query(Resource)
        .join(Metadata, Metadata.sha256 == Resource.sha256)
        .filter(Metadata.is_deleted == 0, Resource.is_deleted == 0)
        .distinct()
        .order_by(func.random())
        .first()
    )

    if resource is None:
        raise HTTPException(status_code=404, detail="No wallpaper found")

    metadata_rows = (
        session.query(Metadata)
        .filter(Metadata.is_deleted == 0, Metadata.sha256 == resource.sha256)
        .all()
    )
    preferred = min(metadata_rows, key=_metadata_priority)

    return RandomWallpaperResponse(
        id=resource.sha256,
        title=preferred.title,
        copyright=preferred.copyright,
        copyrightlink=preferred.copyrightlink,
        width=resource.width,
        height=resource.height,
        image_url=f"/api/images/{resource.sha256}?size=preview",
    )
