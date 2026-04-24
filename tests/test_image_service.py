from pathlib import Path

import pytest
from fastapi import HTTPException

from app.models import Resource
from app.services import image_service


def _insert_resource(db_session, tmp_path, sha, ext="jpg", mime_type="image/jpeg"):
    resource = Resource(
        sha256=sha,
        year=2026,
        month=4,
        base_path=str(tmp_path / sha),
        ext=ext,
        mime_type=mime_type,
        width=1920,
        height=1080,
        bytes=1024,
    )
    db_session.add(resource)
    db_session.commit()
    return resource


def test_serve_image_preview_returns_file_response(db_session, tmp_path):
    sha = "1" * 64
    resource = _insert_resource(db_session, tmp_path, sha)
    preview_path = Path(f"{resource.base_path}_preview.jpg")
    preview_path.write_bytes(b"preview")

    response = image_service.serve_image(db_session, sha, "preview")

    assert response.path == str(preview_path)
    assert response.media_type == "image/jpeg"
    assert response.headers["cache-control"] == "public, max-age=86400"


def test_download_image_sets_attachment_headers(db_session, tmp_path):
    sha = "2" * 64
    resource = _insert_resource(
        db_session,
        tmp_path,
        sha,
        ext="png",
        mime_type="image/png",
    )
    original_path = Path(f"{resource.base_path}.png")
    original_path.write_bytes(b"png")

    response = image_service.download_image(db_session, sha)

    assert response.path == str(original_path)
    assert response.media_type == "image/png"
    assert response.headers["cache-control"] == "public, max-age=86400"
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="{sha}.png"'
    )


def test_serve_image_missing_file_raises_404(db_session, tmp_path):
    sha = "3" * 64
    _insert_resource(db_session, tmp_path, sha)

    with pytest.raises(HTTPException) as exc_info:
        image_service.serve_image(db_session, sha, "preview")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "File not found on disk"
