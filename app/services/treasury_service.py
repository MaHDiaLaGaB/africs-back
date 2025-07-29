from sqlalchemy.orm import Session
from app.models.treasury import Treasury
from app.models.transfer import TreasuryTransfer
from app.logger import Logger

logger = Logger.get_logger(__name__)


def get_employee_balance(db: Session, employee_id: int) -> float:
    treasury = db.query(Treasury).filter_by(employee_id=employee_id).first()
    if not treasury:
        raise ValueError("Treasury not found for employee")
    return treasury.balance


def update_employee_balance(db: Session, employee_id: int, new_balance: float):
    treasury = db.query(Treasury).filter_by(employee_id=employee_id).first()
    if not treasury:
        raise ValueError("Treasury not found for employee")
    treasury.balance = new_balance
    db.commit()


# def modify_employee_balance(db: Session, employee_id: int, amount_delta: float):
#     treasury = db.query(Treasury).filter_by(employee_id=employee_id).first()
#     if not treasury:
#         raise ValueError("Treasury not found")
#     treasury.balance += amount_delta
#     db.commit()

def adjust_employee_balance(
    db: Session,
    employee_id: int,
    delta: float,
    call_id: int | None = None
) -> None:
    tag = f"[{call_id:03d}] " if call_id else ""
    logger.info(
        "%s▶ adjust_employee_balance(emp=%s, delta=%s)",
        tag, employee_id, delta
    )

    treasury = (
        db.query(Treasury)
          .filter(Treasury.employee_id == employee_id)
          .first()
    )
    if not treasury:
        raise ValueError(f"{tag}Treasury not found for employee {employee_id}")

    old = treasury.balance
    treasury.balance += delta
    logger.info(
        "%s   balance: %s → %s",
        tag, old, treasury.balance
    )
    # don’t commit here — let the outer service commit once at the end



def transfer_amount(db: Session, from_id: int, to_id: int, amount: float):
    from_treasury = db.query(Treasury).filter_by(employee_id=from_id).first()
    to_treasury = db.query(Treasury).filter_by(employee_id=to_id).first()

    if from_treasury.balance < amount:
        raise ValueError("Insufficient balance")

    from_treasury.balance -= amount
    to_treasury.balance += amount

    transfer = TreasuryTransfer(
        from_employee_id=from_id, to_employee_id=to_id, amount=amount
    )

    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer
