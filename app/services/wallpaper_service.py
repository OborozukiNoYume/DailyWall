import math

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Metadata, Resource
from app.schemas import WallpaperItem, WallpaperListResponse, WallpaperQueryParams


def list_wallpapers(
    session: Session, params: WallpaperQueryParams
) -> WallpaperListResponse:
    if params.keyword and not any([params.mkt, params.year, params.month]):
        raise ValueError(
            "keyword requires at least one of mkt, year, month"
        )

    base_query = (
        session.query(Metadata, Resource)
        .join(Resource, Metadata.sha256 == Resource.sha256)
        .filter(Metadata.is_deleted == 0, Resource.is_deleted == 0)
    )

    if params.mkt:
        base_query = base_query.filter(Metadata.mkt == params.mkt)
    if params.year:
        base_query = base_query.filter(Resource.year == params.year)
    if params.month:
        base_query = base_query.filter(Resource.month == params.month)

    if params.keyword:
        keyword = f"%{params.keyword}%"
        base_query = base_query.filter(
            or_(
                Metadata.title.ilike(keyword),
                Metadata.copyright.ilike(keyword),
            )
        )

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
