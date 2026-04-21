from app.models import Metadata, Resource


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
    )
    db_session.add(meta)
    db_session.commit()


def test_health(api_client):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_ok"] is True


def test_filters_empty(api_client):
    resp = api_client.get("/api/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert data["markets"] == []
    assert data["years"] == []


def test_wallpapers_empty(api_client):
    resp = api_client.get("/api/wallpapers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


def test_random_wallpaper_empty(api_client):
    resp = api_client.get("/api/wallpapers/random")
    assert resp.status_code == 404


def test_wallpapers_keyword_alone_400(api_client):
    resp = api_client.get("/api/wallpapers?keyword=test")
    assert resp.status_code == 400


def test_image_not_found(api_client):
    resp = api_client.get("/api/images/nonexistent?size=preview")
    assert resp.status_code == 404


def test_download_not_found(api_client):
    resp = api_client.get("/api/images/nonexistent/download")
    assert resp.status_code == 404


def test_wallpapers_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/wallpapers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "b" * 64


def test_random_wallpaper_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/wallpapers/random")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "b" * 64
    assert data["image_url"] == f"/api/images/{'b' * 64}?size=preview"


def test_filters_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "en-US" in data["markets"]
    assert 2026 in data["years"]


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
        )
    )
    db_session.commit()

    resp = api_client.get("/api/wallpapers?dedup=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["mkt"] == ["zh-CN", "en-US"]
    assert data["items"][0]["title"] == "中文标题"
    assert data["items"][0]["date"] == "2026-04-18"
