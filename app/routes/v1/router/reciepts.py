from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.receipt import ReceiptOrder
from app.models.customers import Customer
from app.models.treasury import Treasury
from app.schemas.receipt import ReceiptCreate, ReceiptOut
from app.models.users import User
from app.core.security import get_current_user
from app.dependencies import get_db

router = APIRouter()

@router.post("/create", response_model=ReceiptOut)
def create_receipt(
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    employee: User = Depends(get_current_user)
):
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="العميل غير موجود")

    # خصم من مديونية العميل
    customer.balance_due -= data.amount

    # زيادة رصيد الموظف
    treasury = db.query(Treasury).filter_by(employee_id=employee.id).first()
    treasury.balance += data.amount

    receipt = ReceiptOrder(
        customer_id=customer.id,
        amount=data.amount,
        employee_id=employee.id
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


@router.get("/get", response_model=list[ReceiptOut])
def list_receipts(db: Session = Depends(get_db)):
    return db.query(ReceiptOrder).order_by(ReceiptOrder.created_at.desc()).all()
