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


def test_filters_with_data(api_client, db_session):
    _seed(api_client, db_session)
    resp = api_client.get("/api/filters")
    assert resp.status_code == 200
    data = resp.json()
    assert "en-US" in data["markets"]
    assert 2026 in data["years"]
