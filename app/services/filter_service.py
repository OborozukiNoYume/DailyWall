import time

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models import Metadata, Resource
from app.schemas import FilterOptions

_cache: dict = {}
CACHE_TTL = 86400  # 24 hours


def get_filter_options(session: Session) -> FilterOptions:
    now = time.time()
    if "data" in _cache and _cache["expires_at"] > now:
        return _cache["data"]

    markets = sorted(
        [
            row[0]
            for row in session.query(distinct(Metadata.mkt))
            .filter(Metadata.is_deleted == 0)
            .all()
        ]
    )

    years = sorted(
        [
            row[0]
            for row in session.query(distinct(Resource.year))
            .filter(Resource.is_deleted == 0)
            .all()
        ],
        reverse=True,
    )

    year_month_rows = (
        session.query(Resource.year, Resource.month)
        .filter(Resource.is_deleted == 0)
        .order_by(Resource.year.desc(), Resource.month.asc())
        .all()
    )

    year_months: dict[int, list[int]] = {}
    for y, m in year_month_rows:
        if y not in year_months:
            year_months[y] = set()
        year_months[y].add(m)
    year_months = {y: sorted(ms) for y, ms in sorted(year_months.items(), reverse=True)}

    result = FilterOptions(markets=markets, years=years, year_months=year_months)
    _cache["data"] = result
    _cache["expires_at"] = now + CACHE_TTL

    return result
