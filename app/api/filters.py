from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_session
from app.schemas import FilterOptions
from app.services import filter_service

router = APIRouter()


@router.get("", response_model=FilterOptions)
def get_filters(session: Session = Depends(get_session)):
    return filter_service.get_filter_options(session)
