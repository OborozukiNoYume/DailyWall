import httpx

from app.config import settings

BING_API_URL = "https://www.bing.com/HPImageArchive.aspx"

USER_AGENT = "Mozilla/5.0 (compatible; DailyWall/1.0)"


def _build_client(timeout: float = 30.0) -> httpx.Client:
    transport = httpx.HTTPTransport(retries=3)
    kwargs: dict = {
        "timeout": timeout,
        "follow_redirects": True,
        "headers": {"User-Agent": USER_AGENT},
        "transport": transport,
    }
    if settings.PROXY_URL:
        kwargs["proxy"] = settings.PROXY_URL
    return httpx.Client(**kwargs)


def fetch_images(mkt: str, idx: int = 0, n: int = 1) -> list[dict]:
    params = {
        "format": "js",
        "uhd": "1",
        "idx": str(idx),
        "n": str(n),
        "mkt": mkt,
    }
    with _build_client() as client:
        response = client.get(BING_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("images", [])


def get_uhd_url(image_data: dict) -> str:
    urlbase = image_data.get("urlbase", "")
    if not urlbase:
        return ""
    prefix = "" if urlbase.startswith("http") else "https://www.bing.com"
    return f"{prefix}{urlbase}_UHD.jpg"


def create_http_client(timeout: float = 60.0) -> httpx.Client:
    return _build_client(timeout)
