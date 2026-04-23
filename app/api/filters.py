from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.responses import success_response
from app.database import get_session
from app.schemas import ApiResponse, FilterOptions
from app.services import filter_service

router = APIRouter()


@router.get("", response_model=ApiResponse[FilterOptions])
def get_filters(session: Session = Depends(get_session)):
    data = filter_service.get_filter_options(session)
    return success_response(data)
