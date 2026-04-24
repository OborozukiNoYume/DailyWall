from unittest.mock import MagicMock, patch

from app.config import settings
from app.models import CrawlState, Metadata, Resource
from crawler.crawler import Crawler, CrawlResult
from crawler.downloader import DownloadResult
from scripts import crawl as crawl_script


BING_RESPONSE = [
    {
        "startdate": "20260418",
        "urlbase": "/th?id=OHR.TestImage_en-US1234567890",
        "hsh": "test_hash_abc",
        "title": "Test Title",
        "copyright": "Test Copyright",
        "copyrightlink": "https://www.bing.com/search?q=test",
    }
]


def test_level1_dedup(db_session):
    """Level 1: existing mkt+date skips download."""
    resource = Resource(
        sha256="c" * 64,
        year=2026,
        month=4,
        base_path="wallpaper/2026/04/" + "c" * 64,
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=1000000,
    )
    db_session.add(resource)
    meta = Metadata(
        mkt="en-US",
        date="2026-04-18",
        sha256="c" * 64,
        hsh="existing_hsh",
        title="Existing",
        copyright="Existing Copyright",
    )
    db_session.add(meta)
    db_session.commit()

    crawler = Crawler.__new__(Crawler)
    crawler.engine = db_session.get_bind()

    with patch("crawler.crawler.fetch_images", return_value=BING_RESPONSE):
        with patch("crawler.crawler.download_and_process"):
            success, fail = crawler._crawl_market(db_session, "en-US")

    assert success >= 1
    assert fail == 0
    assert db_session.query(Resource).count() == 1
    refreshed = db_session.query(Metadata).filter_by(mkt="en-US").first()
    assert refreshed is not None
    assert refreshed.copyrightlink == BING_RESPONSE[0]["copyrightlink"]


def test_level2_dedup(db_session):
    """Level 2: existing SHA256 reuses resource, creates new metadata."""
    sha = "d" * 64
    resource = Resource(
        sha256=sha,
        year=2026,
        month=3,
        base_path="wallpaper/2026/03/" + sha,
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=1000000,
    )
    db_session.add(resource)
    meta = Metadata(
        mkt="zh-CN",
        date="2026-03-15",
        sha256=sha,
        hsh="existing_hsh_cn",
        title="CN Title",
        copyright="CN Copyright",
    )
    db_session.add(meta)
    db_session.commit()

    crawler = Crawler.__new__(Crawler)
    crawler.engine = db_session.get_bind()

    mock_response = MagicMock()
    mock_response.content = b"fake image data"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("crawler.crawler.fetch_images", return_value=BING_RESPONSE):
        with patch("crawler.crawler.calculate_sha256", return_value=sha):
            with patch("crawler.crawler.tempfile.mkstemp", return_value=(3, "/tmp/test.jpg")):
                with patch("crawler.crawler.os.fdopen", MagicMock()):
                        with patch("crawler.crawler.os.unlink"):
                            with patch(
                                "crawler.crawler.create_http_client",
                                return_value=mock_client,
                            ):
                                success, fail = crawler._crawl_market(
                                    db_session, "en-US"
                                )

    metas = db_session.query(Metadata).all()
    mkts = {m.mkt for m in metas}
    assert "en-US" in mkts
    assert db_session.query(Resource).count() == 1
    new_meta = db_session.query(Metadata).filter_by(mkt="en-US").first()
    assert new_meta is not None
    assert new_meta.copyrightlink == BING_RESPONSE[0]["copyrightlink"]


def test_init_db_adds_metadata_copyrightlink_column(monkeypatch, tmp_path):
    import sqlite3

    from app.database import init_db

    db_path = tmp_path / "dailywall.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE resources (
                sha256 TEXT PRIMARY KEY,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                base_path TEXT NOT NULL,
                ext TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                bytes INTEGER NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE metadata (
                mkt TEXT NOT NULL,
                date TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                hsh TEXT NOT NULL,
                title TEXT,
                copyright TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (mkt, date)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(settings, "DB_PATH", str(db_path))

    init_db()

    conn = sqlite3.connect(db_path)
    try:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(metadata)")
        }
    finally:
        conn.close()

    assert "copyrightlink" in columns


def test_run_returns_partial_result(db_session, tmp_path):
    crawler = Crawler.__new__(Crawler)
    crawler.engine = db_session.get_bind()
    crawler.lock_path = tmp_path / ".crawl.lock"

    with patch.object(settings, "MARKETS", ["zh-CN", "en-US"]):
        with patch.object(
            Crawler, "_crawl_market", side_effect=[(1, 0), (0, 1)]
        ):
            result = crawler.run()

    assert result == CrawlResult("partial", 1, 1)


def test_process_image_missing_startdate_returns_false(db_session):
    crawler = Crawler.__new__(Crawler)

    result = crawler._process_image(db_session, "en-US", {"title": "No date"})

    assert result is False
    assert db_session.query(Resource).count() == 0
    assert db_session.query(Metadata).count() == 0


def test_process_image_missing_uhd_url_returns_false(db_session):
    crawler = Crawler.__new__(Crawler)

    with patch("crawler.crawler.get_uhd_url", return_value=""):
        result = crawler._process_image(
            db_session,
            "en-US",
            {"startdate": "20260418", "title": "No URL"},
        )

    assert result is False
    assert db_session.query(Resource).count() == 0
    assert db_session.query(Metadata).count() == 0


def test_process_image_new_resource_persists_records(db_session):
    crawler = Crawler.__new__(Crawler)
    sha = "e" * 64
    dl_result = DownloadResult(
        sha256=sha,
        width=3840,
        height=2160,
        mime_type="image/jpeg",
        file_size=543210,
        ext="jpg",
        original_path=f"/tmp/{sha}.jpg",
        thumbnail_path=f"/tmp/{sha}_thumbnail.jpg",
        preview_path=f"/tmp/{sha}_preview.jpg",
        base_path=f"wallpaper/2026/04/{sha}",
    )

    mock_response = MagicMock()
    mock_response.content = b"fake image data"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    with patch("crawler.crawler.get_uhd_url", return_value="https://example.com/uhd.jpg"):
        with patch("crawler.crawler.create_http_client", return_value=mock_client):
            with patch("crawler.crawler.calculate_sha256", return_value=sha):
                with patch(
                    "crawler.crawler.tempfile.mkstemp",
                    return_value=(3, "/tmp/test-new.jpg"),
                ):
                    with patch("crawler.crawler.os.fdopen", MagicMock()):
                        with patch("crawler.crawler.os.unlink"):
                            with patch(
                                "crawler.crawler.download_and_process",
                                return_value=dl_result,
                            ):
                                result = crawler._process_image(
                                    db_session,
                                    "en-US",
                                    {
                                        "startdate": "20260418",
                                        "hsh": "fresh_hsh",
                                        "title": "Fresh Title",
                                        "copyright": "Fresh Copyright",
                                        "copyrightlink": "https://example.com/copyright",
                                    },
                                )

    assert result is True
    resource = db_session.get(Resource, sha)
    assert resource is not None
    assert resource.year == 2026
    assert resource.month == 4
    assert resource.bytes == 543210

    metadata = db_session.query(Metadata).filter_by(mkt="en-US").first()
    assert metadata is not None
    assert metadata.date == "2026-04-18"
    assert metadata.sha256 == sha
    assert metadata.copyrightlink == "https://example.com/copyright"


def test_update_crawl_state_caps_failures_and_resets_on_success(db_session):
    crawler = Crawler.__new__(Crawler)

    for _ in range(12):
        crawler._update_crawl_state(db_session, "en-US", False)

    state = db_session.query(CrawlState).filter_by(mkt="en-US").first()
    assert state is not None
    assert state.consecutive_failures == 10
    assert state.last_success_date is None
    assert state.last_attempt_at is not None

    crawler._update_crawl_state(db_session, "en-US", True)

    db_session.refresh(state)
    assert state.consecutive_failures == 0
    assert state.last_success_date is not None


def test_script_main_returns_nonzero_for_partial(monkeypatch):
    monkeypatch.setattr(crawl_script, "setup_logging", lambda: None)
    monkeypatch.setattr(
        crawl_script.settings.__class__,
        "ensure_dirs",
        lambda self: None,
    )
    monkeypatch.setattr(crawl_script, "init_db", lambda: None)

    class DummyCrawler:
        def run(self):
            return CrawlResult("partial", 87, 1)

    monkeypatch.setattr(crawl_script, "Crawler", DummyCrawler)

    assert crawl_script.main() == 2
