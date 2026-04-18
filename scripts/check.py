import argparse
import hashlib
import sys
from pathlib import Path

from app.config import settings
from app.database import get_crawler_engine
from app.models import CrawlRun, CrawlState, Metadata, Resource
from app.utils.image_utils import validate_image
from sqlalchemy.orm import Session


def daily_inspect(session: Session):
    """Check file existence and basic validity."""
    resources = (
        session.query(Resource).filter(Resource.is_deleted == 0).all()
    )

    missing = []
    invalid = []

    for res in resources:
        for suffix, label in [
            (f".{res.ext}", "original"),
            ("_thumbnail.jpg", "thumbnail"),
            ("_preview.jpg", "preview"),
        ]:
            filepath = f"{res.base_path}{suffix}"
            path = Path(filepath)
            if not path.exists():
                missing.append((res.sha256, label, filepath))
            elif path.stat().st_size == 0:
                invalid.append((res.sha256, label, "empty file"))
            elif label != "original" and not validate_image(filepath):
                invalid.append((res.sha256, label, "corrupt"))

    print(f"Checked {len(resources)} resources")
    if missing:
        print(f"\nMissing files ({len(missing)}):")
        for sha, label, path in missing:
            print(f"  {sha[:12]} {label}: {path}")
    if invalid:
        print(f"\nInvalid files ({len(invalid)}):")
        for sha, label, reason in invalid:
            print(f"  {sha[:12]} {label}: {reason}")
    if not missing and not invalid:
        print("All files OK")


def weekly_inspect(session: Session):
    """SHA256 deep check on originals + daily checks."""
    daily_inspect(session)

    print("\n--- Weekly SHA256 verification ---")
    resources = (
        session.query(Resource).filter(Resource.is_deleted == 0).all()
    )

    mismatch = []
    for res in resources:
        filepath = f"{res.base_path}.{res.ext}"
        path = Path(filepath)
        if not path.exists():
            continue
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        actual = h.hexdigest()
        if actual != res.sha256:
            mismatch.append((res.sha256, actual))

    if mismatch:
        print(f"\nSHA256 mismatches ({len(mismatch)}):")
        for expected, actual in mismatch:
            print(f"  expected: {expected[:12]}  actual: {actual[:12]}")
    else:
        print("All SHA256 checksums OK")


def show_status(session: Session):
    """Show summary status."""
    from sqlalchemy import func

    res_count = (
        session.query(func.count())
        .select_from(Resource)
        .filter(Resource.is_deleted == 0)
        .scalar()
    )
    meta_count = (
        session.query(func.count())
        .select_from(Metadata)
        .filter(Metadata.is_deleted == 0)
        .scalar()
    )

    print(f"Resources: {res_count}")
    print(f"Metadata entries: {meta_count}")

    runs = (
        session.query(CrawlRun)
        .order_by(CrawlRun.run_date.desc())
        .limit(10)
        .all()
    )
    print(f"\nLast {len(runs)} crawl runs:")
    for run in runs:
        print(
            f"  {run.run_date} {run.status} "
            f"success={run.success_count} fail={run.fail_count}"
        )

    states = session.query(CrawlState).all()
    if states:
        print("\nCrawl states:")
        for s in states:
            print(
                f"  {s.mkt}: last_success={s.last_success_date} "
                f"failures={s.consecutive_failures}"
            )


def main():
    parser = argparse.ArgumentParser(description="DailyWall inspector")
    parser.add_argument(
        "mode",
        choices=["daily", "weekly", "status"],
        help="Inspection mode",
    )
    args = parser.parse_args()

    engine = get_crawler_engine()
    session = Session(engine)

    try:
        if args.mode == "daily":
            daily_inspect(session)
        elif args.mode == "weekly":
            weekly_inspect(session)
        elif args.mode == "status":
            show_status(session)
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
