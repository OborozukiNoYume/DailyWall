from unittest.mock import MagicMock

import crawler.bing_fetcher as bing_fetcher


def test_build_client_without_proxy(monkeypatch):
    captured = {}

    class DummyTransport:
        def __init__(self, retries):
            captured["retries"] = retries

    class DummyClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(bing_fetcher.httpx, "HTTPTransport", DummyTransport)
    monkeypatch.setattr(bing_fetcher.httpx, "Client", DummyClient)
    monkeypatch.setattr(bing_fetcher.settings, "PROXY_URL", "")

    client = bing_fetcher._build_client(timeout=12.5)

    assert isinstance(client, DummyClient)
    assert captured["timeout"] == 12.5
    assert captured["follow_redirects"] is True
    assert captured["headers"] == {"User-Agent": bing_fetcher.USER_AGENT}
    assert captured["retries"] == 3
    assert "proxy" not in captured


def test_build_client_with_proxy(monkeypatch):
    captured = {}

    class DummyTransport:
        def __init__(self, retries):
            captured["retries"] = retries

    class DummyClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(bing_fetcher.httpx, "HTTPTransport", DummyTransport)
    monkeypatch.setattr(bing_fetcher.httpx, "Client", DummyClient)
    monkeypatch.setattr(
        bing_fetcher.settings,
        "PROXY_URL",
        "http://127.0.0.1:7890",
    )

    bing_fetcher._build_client(timeout=8.0)

    assert captured["proxy"] == "http://127.0.0.1:7890"
    assert captured["retries"] == 3


def test_fetch_images_requests_expected_params(monkeypatch):
    mock_response = MagicMock()
    mock_response.json.return_value = {"images": [{"id": 1}]}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    monkeypatch.setattr(bing_fetcher, "_build_client", lambda timeout=30.0: mock_client)

    images = bing_fetcher.fetch_images("en-US", idx=2, n=4)

    assert images == [{"id": 1}]
    mock_client.get.assert_called_once_with(
        bing_fetcher.BING_API_URL,
        params={
            "format": "js",
            "uhd": "1",
            "idx": "2",
            "n": "4",
            "mkt": "en-US",
        },
    )
    mock_response.raise_for_status.assert_called_once()


def test_get_uhd_url_handles_relative_absolute_and_empty():
    assert (
        bing_fetcher.get_uhd_url({"urlbase": "/th?id=OHR.Test"})
        == "https://www.bing.com/th?id=OHR.Test_UHD.jpg"
    )
    assert (
        bing_fetcher.get_uhd_url({"urlbase": "https://www.bing.com/th?id=OHR.Test"})
        == "https://www.bing.com/th?id=OHR.Test_UHD.jpg"
    )
    assert bing_fetcher.get_uhd_url({}) == ""


def test_create_http_client_delegates_to_build_client(monkeypatch):
    marker = object()

    def fake_build_client(timeout):
        assert timeout == 45.0
        return marker

    monkeypatch.setattr(bing_fetcher, "_build_client", fake_build_client)

    assert bing_fetcher.create_http_client(timeout=45.0) is marker
