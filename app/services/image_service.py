from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models import Resource


def _resolve_path(
    session: Session, sha256: str, size_type: str
) -> tuple[str, str, Resource]:
    resource = (
        session.query(Resource)
        .filter_by(sha256=sha256, is_deleted=0)
        .first()
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Image not found")

    if size_type == "thumbnail":
        filepath = f"{resource.base_path}_thumbnail.jpg"
        media_type = "image/jpeg"
    elif size_type == "preview":
        filepath = f"{resource.base_path}_preview.jpg"
        media_type = "image/jpeg"
    elif size_type == "original":
        filepath = f"{resource.base_path}.{resource.ext}"
        media_type = resource.mime_type
    else:
        raise HTTPException(status_code=400, detail="size 参数无效")

    if not Path(filepath).exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return filepath, media_type, resource


def serve_image(session: Session, sha256: str, size: str) -> FileResponse:
    filepath, media_type, _ = _resolve_path(session, sha256, size)
    return FileResponse(
        filepath,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


def download_image(session: Session, sha256: str) -> FileResponse:
    filepath, _, resource = _resolve_path(session, sha256, "original")
    filename = f"{sha256}.{resource.ext}"
    return FileResponse(
        filepath,
        media_type=resource.mime_type,
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=86400",
        },
    )
