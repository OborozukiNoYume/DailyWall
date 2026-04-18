from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_session
from app.services import image_service

router = APIRouter()


@router.get("/{id}")
def get_image(
    id: str,
    size: str = Query("preview", pattern="^(thumbnail|preview)$"),
    session: Session = Depends(get_session),
) -> FileResponse:
    return image_service.serve_image(session, id, size)


@router.get("/{id}/download")
def download_image(
    id: str,
    session: Session = Depends(get_session),
) -> FileResponse:
    return image_service.download_image(session, id)
