import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings
from app.database import init_db
from crawler.crawler import Crawler


def setup_logging():
    log_dir = settings.LOG_DIR
    log_file = f"{log_dir}/crawl.log"
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    )
    logger.addHandler(handler)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    logger.addHandler(console)


def main():
    setup_logging()
    settings.ensure_dirs()
    init_db()
    crawler = Crawler()
    crawler.run()


if __name__ == "__main__":
    main()
