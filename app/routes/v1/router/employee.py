from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from app.core.security import get_db, get_current_user
from app.services.report_service import get_daily_summary
from app.models.users import User

router = APIRouter()


@router.get("/daily-summary")
def daily_summary(
    date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_daily_summary(db, current_user.id, date)
