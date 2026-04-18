from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import HealthResponse
from app.services import health_service

router = APIRouter()


@router.get("", response_model=HealthResponse)
def get_health(session: Session = Depends(get_session)):
    return health_service.get_health(session)
