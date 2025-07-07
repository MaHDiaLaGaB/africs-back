from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.transactions import Transaction, PaymentType, TransactionStatus
from app.schemas.transactions import TransactionCreate, TransactionUpdate
from app.models.customers import Customer
from app.models.currency import Currency
from app.models.service import Service
from app.models.users import User
from app.models.currency_lot import CurrencyLot
from app.services.treasury_service import modify_employee_balance
from app.models.trnsx_status_log import TransactionStatusLog
from app.services.allocate_currency import allocate_and_compute  # ← استورد الدالة الجديدة
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

    # 3. تحديد سعر البيع للوحدة (sale_rate)
    if service.operation == "multiply":
        sale_rate = service.price
    else:
        sale_rate = 1.0 / service.price

    # 4. تخصيص الكمية وحساب التفصيل والتكلفة والربح
    report = allocate_and_compute(
        db=db,
        currency=currency,
        needed_amount=data.amount_foreign,
        sale_rate=sale_rate
    )
    # report يحتوي على:
    # - breakdown: قائمة { lot_id, unit_cost, quantity, cost }
    # - total_cost, avg_cost, total_sale, profit

    # 5. إنشاء مرجع الموظف والمعاملة مع القيم المحسوبة
    reference = generate_employee_reference(db, employee)
    txn = Transaction(
        reference       = reference,
        currency_id     = currency.id,
        service_id      = service.id,
        customer_name   = data.customer_name,
        to              = data.to,
        number          = data.number,
        amount_foreign  = data.amount_foreign,
        amount_lyd      = report["total_sale"],      # إجمالي البيع
        payment_type    = data.payment_type,
        profit          = report["profit"],           # صافي الربح
        employee_id     = employee.id,
        customer_id     = data.customer_id,
        status          = TransactionStatus.completed,
        notes          = data.notes,
    )
    db.add(txn)
    db.flush()  # للحصول على txn.id قبل تفاصيل الدفعات

    # 6. تسجيل تفاصيل كل دفعة من report["breakdown"]
    for detail in report["breakdown"]:
        db.add(TransactionCurrencyLot(
            transaction_id = txn.id,
            lot_id         = detail["lot_id"],
            quantity       = detail["quantity"],
            cost_per_unit  = detail["unit_cost"],
        ))

    # 7. تحديث خزينة الموظف أو رصيد العميل بناءً على نوع الدفع
    if data.payment_type == PaymentType.cash:
        modify_employee_balance(db, employee.id, report["total_sale"])
    elif data.customer_id:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer.balance_due += report["total_sale"]
        db.add(customer)

    # 8. حفظ التغييرات وإعادة تحميل المعاملة
    db.commit()
    db.refresh(txn)
    return txn





def update_transaction_status(
    db: Session,
    transaction_id: int,
    new_status: TransactionStatus,
    reason: str,
    modified_by: int
) -> Transaction:
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    old_status = txn.status
    txn.status = new_status
    txn.status_reason = reason

    # إذا كان التحديث إلى "cancelled" ولم يكن ملغيًّا سابقًا
    if new_status == TransactionStatus.cancelled and old_status != TransactionStatus.cancelled:
        # نحتفظ بالمبلغ قبل التعديل
        original_amount_lyd = txn.amount_lyd

        # إعادة المبلغ إلى خزينة الموظف أو تعديل دين العميل
        if txn.payment_type == PaymentType.cash:
            # يخصم من خزينة الموظف المبلغ الذي سبق إضافته
            modify_employee_balance(db, txn.employee_id, -original_amount_lyd)
        elif txn.customer_id:
            customer = db.query(Customer).filter(Customer.id == txn.customer_id).first()
            if customer:
                customer.balance_due -= original_amount_lyd
                db.add(customer)

        # تصفير مبالغ الحوالة كي لا يعتبرها النظام منقولة
        txn.amount_foreign = 0.0
        txn.amount_lyd     = 0.0

    # تكوين سجل التغيير
    log = TransactionStatusLog(
        transaction_id=txn.id,
        previous_status=old_status,
        new_status=new_status,
        reason=reason,
        changed_by=modified_by
    )

    db.add(log)
    db.commit()
    db.refresh(txn)

    return txn
           # ← إرجاع كائن الـ Transaction نفسه


def update_transaction(
    db: Session,
    txn_id: int,
    data: TransactionUpdate,
    modified_by: int
) -> Transaction:
    # 1) load existing txn
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # 2) if amount_foreign changed, fully revert & re-allocate
    if data.amount_foreign is not None and data.amount_foreign != txn.amount_foreign:
        old_foreign = txn.amount_foreign
        old_lyd     = txn.amount_lyd

        # 2a) undo treasury/customer impact
        if txn.payment_type == PaymentType.cash:
            modify_employee_balance(db, txn.employee_id, -old_lyd)
        elif txn.customer_id:
            c = db.query(Customer).filter(Customer.id == txn.customer_id).first()
            if c:
                c.balance_due -= old_lyd
                db.add(c)

        # 2b) release previous lots
        for detail in txn.lot_details:
            cl = db.query(CurrencyLot).filter(CurrencyLot.id == detail.lot_id).first()
            if cl:
                cl.remaining_quantity += detail.quantity
                db.add(cl)
            db.delete(detail)

        # 2c) re-compute new allocation
        sale_rate = (
            txn.service.price
            if txn.service.operation == "multiply"
            else 1.0 / txn.service.price
        )
        report = allocate_and_compute(
            db=db,
            currency=txn.currency,
            needed_amount=data.amount_foreign,
            sale_rate=sale_rate
        )

        # 2d) apply new amounts & lots
        txn.amount_foreign = data.amount_foreign
        txn.amount_lyd     = report["total_sale"]
        txn.profit         = report["profit"]

        for detail in report["breakdown"]:
            db.add(TransactionCurrencyLot(
                transaction_id=txn.id,
                lot_id=detail["lot_id"],
                quantity=detail["quantity"],
                cost_per_unit=detail["unit_cost"],
            ))

        # 2e) re-apply treasury/customer impact
        if txn.payment_type == PaymentType.cash:
            modify_employee_balance(db, txn.employee_id, report["total_sale"])
        elif txn.customer_id:
            c = db.query(Customer).filter(Customer.id == txn.customer_id).first()
            if c:
                c.balance_due += report["total_sale"]
                db.add(c)

    # 3) update *any* other fields
    update_data = data.dict(exclude_unset=True)
    # we’ve already handled amount_foreign, so skip it here
    for field in ("amount_foreign",):
        update_data.pop(field, None)

    for field, value in update_data.items():
        setattr(txn, field, value)

    # 4) commit and return
    db.commit()
    db.refresh(txn)

    # log status change if relevant
    if "status" in data.dict(exclude_unset=True):
        from app.services.transactions_service import update_transaction_status
        update_transaction_status(
            db, txn_id, txn.status, txn.status_reason or "", modified_by
        )

    return txn