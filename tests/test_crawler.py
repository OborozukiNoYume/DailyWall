from unittest.mock import MagicMock, patch

from app.config import settings
from app.models import CrawlState, Metadata, Resource
from crawler.crawler import Crawler, CrawlResult
from scripts import crawl as crawl_script


BING_RESPONSE = [
    {
        "startdate": "20260418",
        "urlbase": "/th?id=OHR.TestImage_en-US1234567890",
        "hsh": "test_hash_abc",
        "title": "Test Title",
        "copyright": "Test Copyright",
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
