from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import crawler.downloader as downloader


class FixedDateTime:
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)


def test_download_and_process_success(monkeypatch, tmp_path):
    monkeypatch.setattr(
        downloader.settings,
        "WALLPAPER_DIR",
        str(tmp_path / "wallpaper"),
    )
    monkeypatch.setattr(downloader, "datetime", FixedDateTime)

    mock_response = MagicMock()
    mock_response.content = b"image-bytes"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    thumb_calls = []
    preview_calls = []

    def fake_thumbnail(src, dst, width):
        thumb_calls.append((src, dst, width))
        Path(dst).write_bytes(b"thumb")

    def fake_preview(src, dst, width):
        preview_calls.append((src, dst, width))
        Path(dst).write_bytes(b"preview")

    monkeypatch.setattr(
        downloader,
        "create_http_client",
        lambda timeout=60.0: mock_client,
    )
    monkeypatch.setattr(downloader, "validate_image", lambda path: True)
    monkeypatch.setattr(downloader, "calculate_sha256", lambda path: "a" * 64)
    monkeypatch.setattr(
        downloader,
        "get_image_info",
        lambda path: ("image/jpeg", 3840, 2160),
    )
    monkeypatch.setattr(downloader, "generate_thumbnail", fake_thumbnail)
    monkeypatch.setattr(downloader, "generate_preview", fake_preview)

    result = downloader.download_and_process("https://example.com/test.jpg")

    expected_base = tmp_path / "wallpaper" / "2026" / "04" / ("a" * 64)
    assert result.sha256 == "a" * 64
    assert result.width == 3840
    assert result.height == 2160
    assert result.file_size == len(b"image-bytes")
    assert result.base_path == str(expected_base)
    assert Path(result.original_path).read_bytes() == b"image-bytes"
    assert Path(result.original_path).stat().st_mode & 0o777 == 0o444
    assert thumb_calls == [
        (
            str(expected_base) + ".jpg",
            str(expected_base) + "_thumbnail.jpg",
            downloader.settings.THUMBNAIL_WIDTH,
        )
    ]
    assert preview_calls == [
        (
            str(expected_base) + ".jpg",
            str(expected_base) + "_preview.jpg",
            downloader.settings.PREVIEW_MAX_WIDTH,
        )
    ]


def test_download_and_process_invalid_image_removes_temp_file(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        downloader.settings,
        "WALLPAPER_DIR",
        str(tmp_path / "wallpaper"),
    )
    monkeypatch.setattr(downloader, "datetime", FixedDateTime)

    mock_response = MagicMock()
    mock_response.content = b"not-an-image"
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response

    captured = {}
    real_mkstemp = downloader.tempfile.mkstemp

    def tracked_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        captured["tmp_path"] = path
        return fd, path

    monkeypatch.setattr(
        downloader,
        "create_http_client",
        lambda timeout=60.0: mock_client,
    )
    monkeypatch.setattr(downloader.tempfile, "mkstemp", tracked_mkstemp)
    monkeypatch.setattr(downloader, "validate_image", lambda path: False)

    with pytest.raises(ValueError, match="Downloaded file is not a valid image"):
        downloader.download_and_process("https://example.com/test.jpg")

    assert "tmp_path" in captured
    assert not Path(captured["tmp_path"]).exists()
