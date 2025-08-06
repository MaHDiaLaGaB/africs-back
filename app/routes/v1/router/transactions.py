from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime, date

from app.schemas.transactions import (
    TransactionCreate,
    TransactionOut,
    TransactionUpdate,
)
from app.models.transactions import Transaction
from app.services.transactions_service import create_transaction, update_transaction
from app.dependencies import get_db
from app.core.security import get_current_user, require_admin
from app.core.websocket import manager
from app.models.users import User

router = APIRouter()


@router.get("/get", response_model=List[TransactionOut])
def get_all_transactions(
    db: Session = Depends(get_db),
    current_admin=Depends(require_admin),
):
    txs = (
        db.query(Transaction)
        .options(
            joinedload(Transaction.employee),  # loads .employee.full_name
            joinedload(Transaction.customer),  # loads .customer.name
        )
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return txs


@router.post("/create", response_model=TransactionOut)
def sell_currency(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_transaction(db, data, current_user)


@router.get(
    "/by_customer/{customer_id}",
    response_model=List[TransactionOut],
    summary="Get all transactions for a given customer",
)
def get_transactions_by_customer(
    customer_id: int,
    db: Session = Depends(get_db),
):
    txs = db.query(Transaction).filter(Transaction.customer_id == customer_id).all()
    if txs is None:
        raise HTTPException(
            status_code=404, detail="No transactions found for this customer"
        )
    return txs


@router.put("/update/{tx_id}", dependencies=[Depends(require_admin)])
async def api_update_transaction(
    tx_id: int,
    request: Request,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    # You can still log raw payload if desired
    raw = await request.json()
    print("🔍 Raw payload:", raw)
    print("✔️ Parsed model:", data)

    try:
        txn = update_transaction(
            db=db, txn_id=tx_id, data=data, modified_by=current_admin.id
        )
    except HTTPException:
        raise  # re-raise 404 or other errors
    return txn


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
