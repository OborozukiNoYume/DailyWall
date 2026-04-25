import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.logging_utils import configure_logging, get_component_logger

logger = get_component_logger("maintenance", __name__)


def setup_logging():
    return configure_logging("maintenance", log_dir=settings.LOG_DIR)


def backup_database():
    setup_logging()
    db_path = Path(settings.DB_PATH).resolve()
    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        sys.exit(1)

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"dailywall_{timestamp}.db"

    source = sqlite3.connect(str(db_path))
    target = sqlite3.connect(str(backup_path))
    source.backup(target)
    target.close()
    source.close()

    logger.info("Backup created: %s", backup_path)

    # Rotate: keep last 30 backups
    backups = sorted(backup_dir.glob("dailywall_*.db"))
    if len(backups) > 30:
        for old in backups[:-30]:
            old.unlink()
            logger.info("Removed old backup: %s", old)


if __name__ == "__main__":
    backup_database()
