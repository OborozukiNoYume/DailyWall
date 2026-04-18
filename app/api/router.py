from fastapi import APIRouter

from app.api import filters, health, images, wallpapers

api_router = APIRouter(prefix="/api")
api_router.include_router(filters.router, prefix="/filters", tags=["filters"])
api_router.include_router(
    wallpapers.router, prefix="/wallpapers", tags=["wallpapers"]
)
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
