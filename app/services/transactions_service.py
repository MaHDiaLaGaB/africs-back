from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.transactions import Transaction, PaymentType, TransactionStatus
from app.schemas.transactions import TransactionCreate
from app.models.customers import Customer
from app.models.currency import Currency
from app.models.service import Service
from app.models.users import User
from app.services.treasury_service import modify_employee_balance
from app.models.trnsx_status_log import TransactionStatusLog
from app.services.allocate_currency import allocate_currency_lots  # where you defined allocate_currency_lots
from app.models.transaction_currency_lot import TransactionCurrencyLot


def generate_employee_reference(db: Session, employee: User) -> str:
    initials = f"{employee.full_name[0]}{employee.username[0]}".upper()
    count = db.query(Transaction).filter(Transaction.employee_id == employee.id).count()
    return f"{initials}{count + 1}"


def create_transaction(db: Session, data: TransactionCreate, employee: User) -> Transaction:
    # 1. جلب الخدمة والتأكد من وجودها وفعلها
    service = (
        db.query(Service)
          .filter(Service.id == data.service_id, Service.is_active == True)
          .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found or inactive")

    # 2. جلب العملة والتأكد من وجودها وفعلها
    currency = (
        db.query(Currency)
          .filter(Currency.id == service.currency_id, Currency.is_active == True)
          .first()
    )
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found or inactive")

    # 3. تخصيص الكمية المطلوبة من دفعات FIFO
    allocations = allocate_currency_lots(db, currency, data.amount_foreign)

    # 4. حساب معدل البيع للوحدة والمبلغ بالليرة
    if service.operation == "multiply":
        unit_sale_rate = service.price
        amount_lyd = round(data.amount_foreign * unit_sale_rate, 2)
    else:
        unit_sale_rate = 1.0 / service.price
        amount_lyd = round(data.amount_foreign * unit_sale_rate, 2)

    # 5. حساب إجمالي الربح بجمع الفروق لكل دفعة
    total_profit = 0.0
    for lot, qty in allocations:
        profit_per_unit = unit_sale_rate - lot.cost_per_unit
        total_profit += round(profit_per_unit * qty, 2)

    # 6. إنشاء مرجع الموظف والمعاملة
    reference = generate_employee_reference(db, employee)
    txn = Transaction(
        reference       = reference,
        currency_id     = currency.id,
        service_id      = service.id,
        customer_name   = data.customer_name,
        to              = data.to,
        number          = data.number,
        amount_foreign  = data.amount_foreign,
        amount_lyd      = amount_lyd,
        payment_type    = data.payment_type,
        profit          = round(total_profit, 2),
        employee_id     = employee.id,
        customer_id     = data.customer_id,
        status          = TransactionStatus.completed,
    )
    db.add(txn)
    db.flush()  # للحصول على txn.id قبل إنشاء تفاصيل الدفعات

    # 7. تسجيل تفاصيل كل دفعة مستهلكة
    for lot, qty in allocations:
        detail = TransactionCurrencyLot(
            transaction_id = txn.id,
            lot_id         = lot.id,
            quantity       = qty,
            cost_per_unit  = lot.cost_per_unit,
        )
        db.add(detail)

    # 8. تحديث خزينة الموظف أو رصيد العميل بناءً على نوع الدفع
    if data.payment_type == PaymentType.cash:
        modify_employee_balance(db, employee.id, amount_lyd)
    elif data.customer_id:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer.balance_due += amount_lyd
        db.add(customer)

    # 9. حفظ التغييرات وإعادة تحميل المعاملة
    db.commit()
    db.refresh(txn)
    return txn


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
