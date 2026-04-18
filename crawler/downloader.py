import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings
from app.utils.image_utils import (
    calculate_sha256,
    generate_preview,
    generate_thumbnail,
    get_image_info,
    validate_image,
)
from crawler.bing_fetcher import create_http_client

USER_AGENT = "Mozilla/5.0 (compatible; DailyWall/1.0)"


@dataclass
class DownloadResult:
    sha256: str
    width: int
    height: int
    mime_type: str
    file_size: int
    ext: str
    original_path: str
    thumbnail_path: str
    preview_path: str
    base_path: str


def download_and_process(url: str) -> DownloadResult:
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    save_dir = Path(settings.WALLPAPER_DIR) / str(year) / f"{month:02d}"
    save_dir.mkdir(parents=True, exist_ok=True)

    with create_http_client(timeout=60.0) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content

    ext = "jpg"
    suffix = f".{ext}"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
    except Exception:
        os.unlink(tmp_path)
        raise

    if not validate_image(tmp_path):
        os.unlink(tmp_path)
        raise ValueError("Downloaded file is not a valid image")

    sha256 = calculate_sha256(tmp_path)
    mime_type, width, height = get_image_info(tmp_path)
    file_size = os.path.getsize(tmp_path)

    base_path = str(save_dir / sha256)
    original_path = f"{base_path}.{ext}"
    thumbnail_path = f"{base_path}_thumbnail.jpg"
    preview_path = f"{base_path}_preview.jpg"

    os.rename(tmp_path, original_path)
    os.chmod(original_path, 0o444)

    generate_thumbnail(original_path, thumbnail_path, settings.THUMBNAIL_WIDTH)
    generate_preview(original_path, preview_path, settings.PREVIEW_MAX_WIDTH)

    return DownloadResult(
        sha256=sha256,
        width=width,
        height=height,
        mime_type=mime_type,
        file_size=file_size,
        ext=ext,
        original_path=original_path,
        thumbnail_path=thumbnail_path,
        preview_path=preview_path,
        base_path=base_path,
    )
