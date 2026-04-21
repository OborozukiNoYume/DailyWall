from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import (
    RandomWallpaperResponse,
    WallpaperListResponse,
    WallpaperQueryParams,
)
from app.services import wallpaper_service

router = APIRouter()


@router.get("/random", response_model=RandomWallpaperResponse)
def get_random_wallpaper(
    session: Session = Depends(get_session),
):
    return wallpaper_service.get_random_wallpaper(session)


@router.get("", response_model=WallpaperListResponse)
def list_wallpapers(
    params: WallpaperQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    try:
        return wallpaper_service.list_wallpapers(session, params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
