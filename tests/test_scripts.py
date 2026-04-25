import logging
import sqlite3
from pathlib import Path

import pytest

from app import logging_utils
from app.models import CrawlRun, CrawlState, Metadata, Resource
from crawler.crawler import CrawlResult
from scripts import backup as backup_script
from scripts import check as check_script
from scripts import crawl as crawl_script


def _insert_resource_with_metadata(db_session, tmp_path, sha):
    resource = Resource(
        sha256=sha,
        year=2026,
        month=4,
        base_path=str(tmp_path / sha),
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=4096,
    )
    db_session.add(resource)
    db_session.add(
        Metadata(
            mkt="zh-CN",
            date="2026-04-18",
            sha256=sha,
            hsh=f"hsh_{sha[:8]}",
            title="Title",
            copyright="Copyright",
        )
    )
    db_session.commit()
    return resource


def _clear_managed_handlers():
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, logging_utils._HANDLER_KEY_ATTR, None):
            root_logger.removeHandler(handler)
            handler.close()


def test_backup_database_missing_db_exits(monkeypatch, tmp_path, capsys):
    _clear_managed_handlers()
    monkeypatch.setattr(
        backup_script.settings, "LOG_DIR", str(tmp_path / "logs")
    )
    monkeypatch.setattr(
        backup_script.settings,
        "DB_PATH",
        str(tmp_path / "missing.db"),
    )

    with pytest.raises(SystemExit) as exc_info:
        backup_script.backup_database()

    assert exc_info.value.code == 1
    assert "Database not found:" in capsys.readouterr().out


def test_backup_database_creates_backup_and_rotates(monkeypatch, tmp_path, capsys):
    _clear_managed_handlers()
    db_path = tmp_path / "dailywall.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    for i in range(31):
        (backup_dir / f"dailywall_20200101_0000{i:02d}.db").write_bytes(b"old")

    monkeypatch.setattr(backup_script.settings, "DB_PATH", str(db_path))
    monkeypatch.setattr(
        backup_script.settings, "LOG_DIR", str(tmp_path / "logs")
    )

    backup_script.backup_database()

    backups = sorted(backup_dir.glob("dailywall_*.db"))
    output = capsys.readouterr().out
    assert len(backups) == 30
    assert "Backup created:" in output
    assert "Removed old backup:" in output


def test_daily_inspect_reports_invalid_files(
    db_session, monkeypatch, tmp_path, capsys
):
    _clear_managed_handlers()
    monkeypatch.setattr(
        check_script.settings, "LOG_DIR", str(tmp_path / "logs")
    )
    resource = _insert_resource_with_metadata(db_session, tmp_path, "a" * 64)
    Path(f"{resource.base_path}.jpg").write_bytes(b"original")
    Path(f"{resource.base_path}_thumbnail.jpg").write_bytes(b"")
    Path(f"{resource.base_path}_preview.jpg").write_bytes(b"preview")

    monkeypatch.setattr(check_script, "validate_image", lambda path: False)

    check_script.daily_inspect(db_session)

    output = capsys.readouterr().out
    assert "Checked 1 resources" in output
    assert "Invalid files (2):" in output
    assert "thumbnail: empty file" in output
    assert "preview: corrupt" in output


def test_weekly_inspect_reports_sha_mismatch(
    db_session, monkeypatch, tmp_path, capsys
):
    _clear_managed_handlers()
    monkeypatch.setattr(
        check_script.settings, "LOG_DIR", str(tmp_path / "logs")
    )
    resource = _insert_resource_with_metadata(db_session, tmp_path, "b" * 64)
    Path(f"{resource.base_path}.jpg").write_bytes(b"not-matching")
    Path(f"{resource.base_path}_thumbnail.jpg").write_bytes(b"thumb")
    Path(f"{resource.base_path}_preview.jpg").write_bytes(b"preview")

    monkeypatch.setattr(check_script, "validate_image", lambda path: True)

    check_script.weekly_inspect(db_session)

    output = capsys.readouterr().out
    assert "All files OK" in output
    assert "SHA256 mismatches (1):" in output


def test_show_status_prints_summary(db_session, monkeypatch, tmp_path, capsys):
    _clear_managed_handlers()
    monkeypatch.setattr(
        check_script.settings, "LOG_DIR", str(tmp_path / "logs")
    )
    _insert_resource_with_metadata(db_session, tmp_path, "c" * 64)
    db_session.add(
        CrawlRun(
            run_date="2026-04-18",
            started_at="2026-04-18T00:00:00",
            finished_at="2026-04-18T00:01:00",
            status="success",
            success_count=1,
            fail_count=0,
        )
    )
    db_session.add(
        CrawlState(
            mkt="zh-CN",
            last_success_date="2026-04-18",
            last_attempt_at="2026-04-18T00:01:00",
            consecutive_failures=0,
        )
    )
    db_session.commit()

    check_script.show_status(db_session)

    output = capsys.readouterr().out
    assert "Resources: 1" in output
    assert "Metadata entries: 1" in output
    assert "Last 1 crawl runs:" in output
    assert "2026-04-18 success success=1 fail=0" in output
    assert "zh-CN: last_success=2026-04-18 failures=0" in output


def test_setup_logging_creates_handlers(monkeypatch, tmp_path):
    _clear_managed_handlers()
    monkeypatch.setattr(crawl_script.settings, "LOG_DIR", str(tmp_path / "logs"))

    crawl_script.setup_logging()

    assert (tmp_path / "logs").exists()
    handler_keys = {
        getattr(handler, logging_utils._HANDLER_KEY_ATTR, None)
        for handler in logging.getLogger().handlers
    }
    assert "crawl:file" in handler_keys
    assert "shared:error" in handler_keys
    assert "shared:console" in handler_keys


def test_setup_logging_is_idempotent(monkeypatch, tmp_path):
    _clear_managed_handlers()
    monkeypatch.setattr(crawl_script.settings, "LOG_DIR", str(tmp_path / "logs"))

    crawl_script.setup_logging()
    crawl_script.setup_logging()

    handler_keys = [
        getattr(handler, logging_utils._HANDLER_KEY_ATTR, None)
        for handler in logging.getLogger().handlers
        if getattr(handler, logging_utils._HANDLER_KEY_ATTR, None)
    ]
    assert handler_keys.count("crawl:file") == 1
    assert handler_keys.count("shared:error") == 1
    assert handler_keys.count("shared:console") == 1


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [("success", 0), ("fail", 1)],
)
def test_crawl_main_returns_expected_code(
    monkeypatch, status, expected_code
):
    monkeypatch.setattr(crawl_script, "setup_logging", lambda: None)
    monkeypatch.setattr(
        crawl_script.settings.__class__,
        "ensure_dirs",
        lambda self: None,
    )
    monkeypatch.setattr(crawl_script, "init_db", lambda: None)

    class DummyCrawler:
        def run(self):
            return CrawlResult(status, 1, 0)

    monkeypatch.setattr(crawl_script, "Crawler", DummyCrawler)

    assert crawl_script.main() == expected_code
