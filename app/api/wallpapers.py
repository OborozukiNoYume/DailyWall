from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_session
from app.schemas import (
    ApiResponse,
    RandomWallpaperResponse,
    WallpaperListResponse,
    WallpaperQueryParams,
)
from app.services import wallpaper_service

router = APIRouter()


@router.get("/random", response_model=ApiResponse[RandomWallpaperResponse])
def get_random_wallpaper(
    session: Session = Depends(get_session),
):
    data = wallpaper_service.get_random_wallpaper(session)
    return success_response(data)


@router.get("", response_model=ApiResponse[WallpaperListResponse])
def list_wallpapers(
    params: WallpaperQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    try:
        data = wallpaper_service.list_wallpapers(session, params)
        return success_response(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
