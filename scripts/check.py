import argparse
import hashlib
from pathlib import Path

from app.config import settings
from app.database import get_crawler_engine
from app.logging_utils import configure_logging, get_component_logger
from app.models import CrawlRun, CrawlState, Metadata, Resource
from app.utils.image_utils import validate_image
from sqlalchemy.orm import Session

logger = get_component_logger("maintenance", __name__)


def setup_logging():
    return configure_logging("maintenance", log_dir=settings.LOG_DIR)


def daily_inspect(session: Session):
    """Check file existence and basic validity."""
    setup_logging()
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

    logger.info("Checked %d resources", len(resources))
    if missing:
        logger.warning("Missing files (%d):", len(missing))
        for sha, label, path in missing:
            logger.warning("%s %s: %s", sha[:12], label, path)
    if invalid:
        logger.warning("Invalid files (%d):", len(invalid))
        for sha, label, reason in invalid:
            logger.warning("%s %s: %s", sha[:12], label, reason)
    if not missing and not invalid:
        logger.info("All files OK")


def weekly_inspect(session: Session):
    """SHA256 deep check on originals + daily checks."""
    setup_logging()
    daily_inspect(session)

    logger.info("--- Weekly SHA256 verification ---")
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
        logger.error("SHA256 mismatches (%d):", len(mismatch))
        for expected, actual in mismatch:
            logger.error(
                "expected: %s  actual: %s", expected[:12], actual[:12]
            )
    else:
        logger.info("All SHA256 checksums OK")


def show_status(session: Session):
    """Show summary status."""
    setup_logging()
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

    logger.info("Resources: %s", res_count)
    logger.info("Metadata entries: %s", meta_count)

    runs = (
        session.query(CrawlRun)
        .order_by(CrawlRun.run_date.desc())
        .limit(10)
        .all()
    )
    logger.info("Last %d crawl runs:", len(runs))
    for run in runs:
        logger.info(
            "%s %s success=%d fail=%d",
            run.run_date,
            run.status,
            run.success_count,
            run.fail_count,
        )

    states = session.query(CrawlState).all()
    if states:
        logger.info("Crawl states:")
        for s in states:
            logger.info(
                "%s: last_success=%s failures=%s",
                s.mkt,
                s.last_success_date,
                s.consecutive_failures,
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
