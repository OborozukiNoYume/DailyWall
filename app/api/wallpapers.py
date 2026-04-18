from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import WallpaperListResponse, WallpaperQueryParams
from app.services import wallpaper_service

router = APIRouter()


@router.get("", response_model=WallpaperListResponse)
def list_wallpapers(
    params: WallpaperQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    try:
        return wallpaper_service.list_wallpapers(session, params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
