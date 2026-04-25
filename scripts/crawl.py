from app.config import settings
from app.database import init_db
from app.logging_utils import configure_logging, get_component_logger
from crawler.crawler import Crawler

logger = get_component_logger("crawl", __name__)


def setup_logging():
    return configure_logging("crawl", log_dir=settings.LOG_DIR)


def main():
    setup_logging()
    settings.ensure_dirs()
    init_db()
    logger.info("Starting crawl run for %d markets", len(settings.MARKETS))
    crawler = Crawler()
    result = crawler.run()
    logger.info(
        "Crawl script exit status=%s success=%d fail=%d",
        result.status,
        result.success_count,
        result.fail_count,
    )

    if result.status == "success":
        return 0
    if result.status == "partial":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
