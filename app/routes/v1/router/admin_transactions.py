from fastapi import Depends, HTTPException, APIRouter, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.core.security import require_admin
from app.models.transactions import Transaction
from app.models.transaction_audit import TransactionAudit
from app.models.users import User
from app.models.currency import Currency
from app.schemas.transactions import TransactionStatusUpdate
from app.services.transactions_service import update_transaction_status
from app.models.trnsx_status_log import TransactionStatusLog


router = APIRouter()


@router.put("/transaction/{tx_id}/status")
def change_status(
    tx_id: int,
    status_data: TransactionStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    return update_transaction_status(
        db,
        transaction_id=tx_id,
        new_status=status_data.status,
        reason=status_data.reason,
        modified_by=current_admin.id,
    )


@router.put("/transaction/{tx_id}/cancel", dependencies=[Depends(require_admin)])
def cancel_transaction(tx_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.reference += "_CANCELLED"
    db.commit()
    return {"detail": "Transaction cancelled"}


@router.get("/transaction/{tx_id}/audits")
def get_audit_log(tx_id: int, db: Session = Depends(get_db)):
    return (
        db.query(TransactionAudit)
        .filter_by(transaction_id=tx_id)
        .order_by(TransactionAudit.timestamp.desc())
        .all()
    )


@router.put("/currency/{currency_id}/add-stock")
def add_currency_stock(
    currency_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    currency = db.query(Currency).filter(Currency.id == currency_id).first()
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    currency.stock += amount
    db.commit()
    return {"message": f"Added {amount} to {currency.name} stock"}
