from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_session
from app.schemas import ApiResponse, HealthResponse
from app.services import health_service

router = APIRouter()


@router.get("", response_model=ApiResponse[HealthResponse])
def get_health(session: Session = Depends(get_session)):
    data = health_service.get_health(session)
    return success_response(data)
