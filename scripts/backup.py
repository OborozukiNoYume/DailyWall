import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def backup_database():
    db_path = Path(settings.DB_PATH).resolve()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
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

    print(f"Backup created: {backup_path}")

    # Rotate: keep last 30 backups
    backups = sorted(backup_dir.glob("dailywall_*.db"))
    if len(backups) > 30:
        for old in backups[:-30]:
            old.unlink()
            print(f"Removed old backup: {old}")


if __name__ == "__main__":
    backup_database()
