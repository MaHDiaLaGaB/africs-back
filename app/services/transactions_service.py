from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.transactions import Transaction, PaymentType, TransactionStatus
from app.schemas.transactions import TransactionCreate
from app.models.customers import Customer
from app.models.currency import Currency
from app.models.service import Service
from app.models.users import User
from app.services.treasury_service import modify_employee_balance
from app.models.transaction_audit import TransactionAudit
from app.models.trnsx_status_log import TransactionStatusLog


def create_transaction(db: Session, data: TransactionCreate, employee: User):
    # جلب الخدمة المرتبطة
    service = (
        db.query(Service)
        .filter(Service.id == data.service_id, Service.is_active == True)
        .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found or inactive")

    # جلب العملة المرتبطة بالخدمة
    currency = db.query(Currency).filter(Currency.id == service.currency_id).first()
    if not currency or not currency.is_active:
        raise HTTPException(status_code=404, detail="Currency not found or inactive")

    # تحقق من توفر المخزون الكافي
    if currency.stock < data.amount_foreign:
        raise HTTPException(status_code=400, detail="Insufficient currency stock")

    # حساب المبلغ بالدينار الليبي حسب نوع العملية
    if service.operation == "multiply":
        amount_lyd = round(data.amount_foreign * service.price, 2)
    else:
        amount_lyd = round(data.amount_foreign / service.price, 2)

    # حساب الربح
    profit = (
        round((service.price - currency.cost_per_unit) * data.amount_foreign, 2)
        if service.operation == "multiply"
        else round(
            ((1 / service.price) - currency.cost_per_unit) * data.amount_foreign, 2
        )
    )

    # توليد الرقم المرجعي للموظف
    reference = generate_employee_reference(db, employee)

    # إنشاء الحوالة
    txn = Transaction(
        reference=reference,
        currency_id=currency.id,
        service_id=service.id,
        customer_name=data.customer_name,
        to=data.to,
        number=data.number,
        amount_foreign=data.amount_foreign,
        amount_lyd=amount_lyd,
        payment_type=data.payment_type,
        profit=profit,
        employee_id=employee.id,
        customer_id=data.customer_id,
        status=TransactionStatus.completed,  # أو pending إذا أردت حالة أولية
    )

    db.add(txn)

    # خصم كمية العملة من المخزون
    currency.stock -= data.amount_foreign

    # في حالة الدفع النقدي، أضف المبلغ إلى خزينة الموظف
    if data.payment_type == PaymentType.cash:
        modify_employee_balance(db, employee.id, amount_lyd)
    else:
        # مديونية العميل
        if data.customer_id:
            customer = (
                db.query(Customer).filter(Customer.id == data.customer_id).first()
            )
            if not customer:
                raise HTTPException(status_code=404, detail="Customer not found")
            customer.balance_due += amount_lyd

    db.commit()
    db.refresh(txn)
    return txn


def generate_employee_reference(db: Session, employee):
    initials = f"{employee.full_name[0]}{employee.username[0]}".upper()
    count = db.query(Transaction).filter(Transaction.employee_id == employee.id).count()
    return f"{initials}{count + 1}"


def update_transaction_status(db, transaction_id, new_status, reason, modified_by):
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    old_status = txn.status
    txn.status = new_status

    log = TransactionStatusLog(
        transaction_id=txn.id,
        previous_status=old_status,
        new_status=new_status,
        reason=reason,
        changed_by=modified_by
    )

    db.add(log)
    db.commit()
    return {"detail": "Status updated successfully"}
