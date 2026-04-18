from sqlalchemy import distinct, func, text
from sqlalchemy.orm import Session

from app.models import CrawlRun, CrawlState, Metadata, Resource
from app.schemas import HealthResponse


def get_health(session: Session) -> HealthResponse:
    db_ok = True
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    wallpaper_count = (
        session.query(func.count())
        .select_from(Metadata)
        .filter(Metadata.is_deleted == 0)
        .scalar()
        or 0
    )

    resource_count = (
        session.query(func.count())
        .select_from(Resource)
        .filter(Resource.is_deleted == 0)
        .scalar()
        or 0
    )

    markets_count = (
        session.query(func.count(distinct(CrawlState.mkt))).scalar() or 0
    )

    last_run = (
        session.query(CrawlRun)
        .filter(CrawlRun.status == "success")
        .order_by(CrawlRun.finished_at.desc())
        .first()
    )

    last_success_at = last_run.finished_at if last_run else None

    status = "healthy" if db_ok else "unhealthy"

    return HealthResponse(
        status=status,
        db_ok=db_ok,
        last_success_at=last_success_at,
        wallpaper_count=wallpaper_count,
        resource_count=resource_count,
        markets_count=markets_count,
    )
