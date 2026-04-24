from fastapi.testclient import TestClient

from app.main import app
from app.services import health_service
from app.models import CrawlRun, CrawlState, Metadata, Resource


def _seed(api_client, db_session):
    sha = "b" * 64
    resource = Resource(
        sha256=sha,
        year=2026,
        month=4,
        base_path="wallpaper/2026/04/" + sha,
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=1000000,
    )
    db_session.add(resource)
    meta = Metadata(
        mkt="en-US",
        date="2026-04-17",
        sha256=sha,
        hsh="api_test_hsh",
        title="API Test",
        copyright="API Copyright",
        copyrightlink="https://www.bing.com/search?q=api-test",
    )
    db_session.add(meta)
    db_session.commit()


def _assert_success(resp):
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 200
    assert payload["msg"] == "success"
    return payload["data"]


def test_health(api_client):
    resp = api_client.get("/api/health")
    data = _assert_success(resp)
    assert data["status"] == "healthy"
    assert data["db_ok"] is True
    assert data["last_success_at"] is None
    assert data["wallpaper_count"] == 0
    assert data["resource_count"] == 0
    assert data["markets_count"] == 0


def test_filters_empty(api_client):
    resp = api_client.get("/api/filters")
    data = _assert_success(resp)
    assert data["markets"] == []
    assert data["years"] == []
    assert data["year_months"] == {}


def test_wallpapers_empty(api_client):
    resp = api_client.get("/api/wallpapers")
    data = _assert_success(resp)
    assert data["total"] == 0


def test_random_wallpaper_empty(api_client):
    resp = api_client.get("/api/wallpapers/random")
    assert resp.status_code == 404
    data = resp.json()
    assert data == {"code": 404, "msg": "未找到数据", "data": None}


def test_wallpapers_keyword_alone_400(api_client):
    resp = api_client.get("/api/wallpapers?keyword=test")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 400
    assert (
        data["msg"]
        == "参数错误：keyword 必须搭配 mkt、year、month、date、date_from、date_to 之一"
    )
    assert data["data"] is None


def test_wallpapers_exact_date_filter(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/wallpapers?date=2026-04-17")
    data = _assert_success(resp)
    assert data["total"] == 1
    assert data["items"][0]["date"] == "2026-04-17"


def test_wallpapers_date_range_filter(api_client, db_session):
    sha = "d" * 64
    resource = Resource(
        sha256=sha,
        year=2026,
        month=4,
        base_path="wallpaper/2026/04/" + sha,
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=1000000,
    )
    db_session.add(resource)
    db_session.add(
        Metadata(
            mkt="en-US",
            date="2026-04-20",
            sha256=sha,
            hsh="api_test_hsh_range",
            title="API Range Test",
            copyright="API Range Copyright",
            copyrightlink="https://www.bing.com/search?q=api-range-test",
        )
    )
    db_session.commit()

    resp = api_client.get(
        "/api/wallpapers?date_from=2026-04-18&date_to=2026-04-21"
    )
    data = _assert_success(resp)
    assert data["total"] == 1
    assert data["items"][0]["date"] == "2026-04-20"


def test_wallpapers_date_conflict_400(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get(
        "/api/wallpapers?date=2026-04-17&date_from=2026-04-01"
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 400
    assert data["msg"] == "参数错误：date 不能与 date_from 或 date_to 同时使用"
    assert data["data"] is None


def test_wallpapers_invalid_date_range_400(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get(
        "/api/wallpapers?date_from=2026-04-20&date_to=2026-04-10"
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 400
    assert data["msg"] == "参数错误：date_from 不能晚于 date_to"
    assert data["data"] is None


def test_image_not_found(api_client):
    resp = api_client.get("/api/images/nonexistent?size=preview")
    assert resp.status_code == 404
    data = resp.json()
    assert data == {"code": 404, "msg": "未找到数据", "data": None}


def test_download_not_found(api_client):
    resp = api_client.get("/api/images/nonexistent/download")
    assert resp.status_code == 404
    data = resp.json()
    assert data == {"code": 404, "msg": "未找到数据", "data": None}


def test_image_invalid_size_400(api_client):
    resp = api_client.get("/api/images/nonexistent?size=original")
    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == 400
    assert data["msg"] == "参数错误：size 格式无效"
    assert data["data"] is None


def test_wallpapers_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/wallpapers")
    data = _assert_success(resp)
    assert data["total"] == 1
    assert data["items"][0]["id"] == "b" * 64
    assert (
        data["items"][0]["copyrightlink"]
        == "https://www.bing.com/search?q=api-test"
    )


def test_random_wallpaper_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/wallpapers/random")
    data = _assert_success(resp)
    assert data["id"] == "b" * 64
    assert data["title"] == "API Test"
    assert data["copyright"] == "API Copyright"
    assert data["copyrightlink"] == "https://www.bing.com/search?q=api-test"
    assert data["width"] == 1920
    assert data["height"] == 1080
    assert data["image_url"] == f"/api/images/{'b' * 64}?size=preview"


def test_filters_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/filters")
    data = _assert_success(resp)
    assert "en-US" in data["markets"]
    assert 2026 in data["years"]
    assert data["year_months"] == {"2026": [4]}


def test_health_with_aggregated_data(api_client, db_session):
    _seed(api_client, db_session)
    db_session.add(
        CrawlState(
            mkt="en-US",
            last_success_date="2026-04-17",
            last_attempt_at="2026-04-17T00:00:00",
            consecutive_failures=0,
        )
    )
    db_session.add(
        CrawlRun(
            run_date="2026-04-17",
            started_at="2026-04-17T00:00:00",
            finished_at="2026-04-17T00:01:00",
            status="success",
            success_count=1,
            fail_count=0,
        )
    )
    db_session.commit()

    resp = api_client.get("/api/health")
    data = _assert_success(resp)
    assert data["status"] == "healthy"
    assert data["db_ok"] is True
    assert data["last_success_at"] == "2026-04-17T00:01:00"
    assert data["wallpaper_count"] == 1
    assert data["resource_count"] == 1
    assert data["markets_count"] == 1


def test_wallpapers_dedup_mode(api_client, db_session):
    sha = "c" * 64
    resource = Resource(
        sha256=sha,
        year=2026,
        month=4,
        base_path="wallpaper/2026/04/" + sha,
        ext="jpg",
        mime_type="image/jpeg",
        width=1920,
        height=1080,
        bytes=1000000,
    )
    db_session.add(resource)
    db_session.add(
        Metadata(
            mkt="en-US",
            date="2026-04-19",
            sha256=sha,
            hsh="api_test_hsh_en",
            title="English Title",
            copyright="English Copyright",
            copyrightlink="https://www.bing.com/search?q=english",
        )
    )
    db_session.add(
        Metadata(
            mkt="zh-CN",
            date="2026-04-18",
            sha256=sha,
            hsh="api_test_hsh_zh",
            title="中文标题",
            copyright="中文版权",
            copyrightlink="https://www.bing.com/search?q=zh",
        )
    )
    db_session.commit()

    resp = api_client.get("/api/wallpapers?dedup=true")
    data = _assert_success(resp)
    assert data["total"] == 1
    assert data["items"][0]["mkt"] == ["zh-CN", "en-US"]
    assert data["items"][0]["title"] == "中文标题"
    assert data["items"][0]["date"] == "2026-04-18"
    assert data["items"][0]["copyrightlink"] == "https://www.bing.com/search?q=zh"


def test_health_unexpected_error_500(api_client, monkeypatch):
    def _raise(_session):
        raise RuntimeError("boom")

    monkeypatch.setattr(health_service, "get_health", _raise)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/health")
    assert resp.status_code == 500
    data = resp.json()
    assert data == {"code": 500, "msg": "服务器异常", "data": None}
