from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date

from app.schemas.transactions import TransactionCreate, TransactionOut
from app.models.transactions import Transaction
from app.services.transactions_service import create_transaction
from app.dependencies import get_db
from app.core.security import get_current_user, require_admin
from app.models.users import User

router = APIRouter()


@router.get("/get", response_model=List[TransactionOut])
def get_all_transactions(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    return db.query(Transaction).order_by(Transaction.created_at.desc()).all()

@router.post("/create", response_model=TransactionOut)
def sell_currency(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_transaction(db, data, current_user)


@router.get("/me", response_model=List[TransactionOut])
def get_my_transactions(
    status: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.employee_id == current_user.id)

    if status:
        query = query.filter(Transaction.status == status)
    if payment_type:
        query = query.filter(Transaction.payment_type == payment_type)
    if start_date and end_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Transaction.created_at.between(start_dt, end_dt))

    return query.order_by(Transaction.created_at.desc()).all()
