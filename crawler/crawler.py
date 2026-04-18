import fcntl
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_crawler_engine
from app.models import CrawlRun, CrawlState, Metadata, Resource
from app.utils.image_utils import calculate_sha256
from crawler.bing_fetcher import create_http_client, fetch_images, get_uhd_url
from crawler.downloader import download_and_process

logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self):
        self.engine = get_crawler_engine()
        self.lock_path = Path(settings.DB_PATH).parent / ".crawl.lock"

    def run(self) -> None:
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        today = now.strftime("%Y-%m-%d")

        lock_fd = None
        try:
            lock_fd = open(self.lock_path, "w")
        except OSError:
            logger.error("Cannot create lock file: %s", self.lock_path)
            return

        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            logger.warning("Another crawl is already running, skipping")
            lock_fd.close()
            return

        session = Session(self.engine)
        total_success = 0
        total_fail = 0
        message_parts = []

        try:
            for mkt in settings.MARKETS:
                try:
                    s, f = self._crawl_market(session, mkt)
                    total_success += s
                    total_fail += f
                except Exception as e:
                    total_fail += 1
                    msg = f"Market {mkt} failed: {e}"
                    message_parts.append(msg)
                    logger.error(msg)

            if total_fail == 0:
                status = "success"
            elif total_success == 0:
                status = "fail"
            else:
                status = "partial"

            message = "; ".join(message_parts) if message_parts else None

            run = CrawlRun(
                run_date=today,
                started_at=now_str,
                finished_at=datetime.now(timezone.utc).isoformat(),
                status=status,
                success_count=total_success,
                fail_count=total_fail,
                message=message,
            )
            session.add(run)
            session.commit()
            logger.info(
                "Crawl finished: status=%s success=%d fail=%d",
                status,
                total_success,
                total_fail,
            )
        except Exception as e:
            session.rollback()
            logger.error("Crawl error: %s", e)
        finally:
            session.close()
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()

    def _crawl_market(self, session: Session, mkt: str) -> tuple[int, int]:
        success_count = 0
        fail_count = 0
        had_success = False

        try:
            images = fetch_images(mkt, idx=0, n=8)
        except Exception as e:
            logger.error("Failed to fetch images for %s: %s", mkt, e)
            self._update_crawl_state(session, mkt, False)
            return 0, 1

        for img_data in images:
            try:
                result = self._process_image(session, mkt, img_data)
                if result:
                    had_success = True
                    success_count += 1
            except Exception as e:
                fail_count += 1
                logger.error(
                    "Failed to process image for %s: %s", mkt, e
                )

        self._update_crawl_state(session, mkt, had_success)
        return success_count, fail_count

    def _process_image(
        self, session: Session, mkt: str, img_data: dict
    ) -> bool:
        startdate = img_data.get("startdate", "")
        if not startdate:
            logger.warning("Missing startdate, skipping")
            return False

        date = f"{startdate[:4]}-{startdate[4:6]}-{startdate[6:8]}"
        hsh = img_data.get("hsh", "")
        title = img_data.get("title", "")
        copyright_info = img_data.get("copyright", "")

        # Level 1 dedup: check mkt + date
        existing = (
            session.query(Metadata)
            .filter_by(mkt=mkt, date=date, is_deleted=0)
            .first()
        )
        if existing:
            logger.debug("Level 1 dedup hit: %s %s", mkt, date)
            return True

        url = get_uhd_url(img_data)
        if not url:
            logger.warning("Cannot construct UHD URL, skipping")
            return False

        # Download to temp to compute SHA256
        with create_http_client(timeout=60.0) as client:
            response = client.get(url)
            response.raise_for_status()
            content = response.content

        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            sha256 = calculate_sha256(tmp_path)
        finally:
            os.unlink(tmp_path)

        # Level 2 dedup: check SHA256
        existing_resource = (
            session.query(Resource)
            .filter_by(sha256=sha256, is_deleted=0)
            .first()
        )
        if existing_resource:
            meta = Metadata(
                mkt=mkt,
                date=date,
                sha256=sha256,
                hsh=hsh,
                title=title,
                copyright=copyright_info,
            )
            session.add(meta)
            session.commit()
            logger.info(
                "Level 2 dedup hit: new metadata for existing resource %s",
                sha256[:12],
            )
            return True

        # New image: full download and process
        dl_result = download_and_process(url)

        # Update SHA256 from actual download
        resource = Resource(
            sha256=dl_result.sha256,
            year=int(dl_result.base_path.split("/")[-3]),
            month=int(dl_result.base_path.split("/")[-2]),
            base_path=dl_result.base_path,
            ext=dl_result.ext,
            mime_type=dl_result.mime_type,
            width=dl_result.width,
            height=dl_result.height,
            bytes=dl_result.file_size,
        )
        session.add(resource)

        meta = Metadata(
            mkt=mkt,
            date=date,
            sha256=dl_result.sha256,
            hsh=hsh,
            title=title,
            copyright=copyright_info,
        )
        session.add(meta)
        session.commit()
        logger.info("New wallpaper: %s -> %s", title, dl_result.sha256[:12])
        return True

    def _update_crawl_state(
        self, session: Session, mkt: str, success: bool
    ) -> None:
        now_str = datetime.now(timezone.utc).isoformat()

        state = session.query(CrawlState).filter_by(mkt=mkt).first()
        if state is None:
            state = CrawlState(mkt=mkt)
            session.add(state)

        state.last_attempt_at = now_str
        if success:
            state.last_success_date = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d"
            )
            state.consecutive_failures = 0
        else:
            state.consecutive_failures = min(
                (state.consecutive_failures or 0) + 1, 10
            )

        session.commit()
