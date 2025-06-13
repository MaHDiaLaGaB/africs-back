from sqlalchemy.orm import Session
from app.models.receipt import ReceiptOrder
from app.models.customers import Customer
from app.models.users import User
from app.services.treasury_service import modify_employee_balance


def create_receipt(
    db: Session, employee: User, customer_id: int, amount: float
) -> ReceiptOrder:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError("Customer not found")

    receipt = ReceiptOrder(
        amount=amount, employee_id=employee.id, customer_id=customer_id
    )

    # تخفيض مديونية العميل
    customer.balance_due -= amount
    # زيادة رصيد الموظف
    modify_employee_balance(db, employee.id, amount)

    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt
