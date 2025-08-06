from fastapi import Depends, HTTPException, APIRouter, status
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.core.security import require_admin
from app.core.websocket import manager
from app.models.transactions import Transaction
from app.models.transaction_audit import TransactionAudit
from app.models.users import User
from app.schemas.transactions import TransactionStatusUpdate
from app.services.transactions_service import update_transaction_status
from app.models.trnsx_status_log import TransactionStatusLog


router = APIRouter()


@router.put("/transaction/{tx_id}/status")
async def change_status(
    tx_id: int,
    status_data: TransactionStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):  # TODO add relation between employee adn transaction
    txn = update_transaction_status(
        db,
        transaction_id=tx_id,
        new_status=status_data.status,
        reason=status_data.reason,
        modified_by=current_admin.id,
    )
    # Notify the employee about status change
    await manager.broadcast(
        {
            "type": "status_update",
            "content": f"تم تغيير حالة الحوالة #{tx_id} إلى {status_data.status}",
        }
    )
    return txn


@router.put("/transaction/{tx_id}/cancel", dependencies=[Depends(require_admin)])
async def cancel_transaction(tx_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.reference += "_CANCELLED"
    db.commit()
    await manager.broadcast(
        {"type": "transaction_cancelled", "content": f"تم إلغاء الحوالة #{tx_id}"}
    )
    return {"detail": "Transaction cancelled"}


@router.get("/transaction/{tx_id}/audits")
def get_audit_log(tx_id: int, db: Session = Depends(get_db)):
    return (
        db.query(TransactionAudit)
        .filter_by(transaction_id=tx_id)
        .order_by(TransactionAudit.timestamp.desc())
        .all()
    )


@router.get(
    "/transaction/{tx_id}/status-log",
    response_model=List[dict],
    dependencies=[Depends(require_admin)],
)
def get_status_log(
    tx_id: int,
    db: Session = Depends(get_db),
):
    logs = (
        db.query(TransactionStatusLog)
        .filter(TransactionStatusLog.transaction_id == tx_id)
        .order_by(TransactionStatusLog.changed_at.desc())
        .all()
    )

    if not logs:
        # return empty list rather than 404, so the frontend just shows “no logs”
        return []

    return [
        {
            "previous_status": log.previous_status.value,
            "new_status": log.new_status.value,
            "reason": log.reason,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at.isoformat(),
        }
        for log in logs
    ]
