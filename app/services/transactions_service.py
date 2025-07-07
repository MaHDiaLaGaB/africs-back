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
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # 1) detect a change in amount_foreign
    if data.amount_foreign is not None and data.amount_foreign != txn.amount_foreign:
        old_foreign = txn.amount_foreign
        new_foreign = data.amount_foreign
        delta_foreign = new_foreign - old_foreign

        # determine sale_rate
        sale_rate = (
            txn.service.price
            if txn.service.operation == "multiply"
            else 1.0 / txn.service.price
        )

        # POSITIVE DELTA → allocate only the extra amount
        if delta_foreign > 0:
            report = allocate_and_compute(
                db=db,
                currency=txn.currency,
                needed_amount=delta_foreign,
                sale_rate=sale_rate
            )

            # append new lot allocations
            for d in report["breakdown"]:
                db.add(TransactionCurrencyLot(
                    transaction_id=txn.id,
                    lot_id=d["lot_id"],
                    quantity=d["quantity"],
                    cost_per_unit=d["unit_cost"],
                ))

            # adjust balances by the extra LYD
            extra_sale   = report["total_sale"]
            extra_profit = report["profit"]
            if txn.payment_type == PaymentType.cash:
                modify_employee_balance(db, txn.employee_id, extra_sale)
            elif txn.customer_id:
                c = db.query(Customer).filter(Customer.id == txn.customer_id).first()
                if c:
                    c.balance_due += extra_sale
                    db.add(c)

            # update the transaction fields incrementally
            txn.amount_lyd += extra_sale
            txn.profit     += extra_profit

        # NEGATIVE DELTA → de-allocate just the over-allocated amount
        else:
            to_release = -delta_foreign
            sale_to_deduct   = round(to_release * sale_rate, 2)
            profit_to_deduct = 0.0

            # walk through existing lot_details in reverse insertion order
            for detail in sorted(txn.lot_details, key=lambda d: d.id, reverse=True):
                if to_release <= 0:
                    break

                take = min(detail.quantity, to_release)
                # restore that qty back to its CurrencyLot
                cl = db.query(CurrencyLot).get(detail.lot_id)
                cl.remaining_quantity += take
                db.add(cl)

                # compute profit removal = (sale_rate * qty) - (cost_per_unit * qty)
                profit_to_deduct += round(sale_rate * take - detail.cost_per_unit * take, 2)

                # shrink or remove the detail record
                detail.quantity -= take
                if detail.quantity <= 0:
                    db.delete(detail)
                else:
                    db.add(detail)

                to_release -= take

            # adjust balances by the deducted LYD
            if txn.payment_type == PaymentType.cash:
                modify_employee_balance(db, txn.employee_id, -sale_to_deduct)
            elif txn.customer_id:
                c = db.query(Customer).filter(Customer.id == txn.customer_id).first()
                if c:
                    c.balance_due -= sale_to_deduct
                    db.add(c)

            # apply to transaction fields
            txn.amount_lyd -= sale_to_deduct
            txn.profit     -= profit_to_deduct

        # finally, update the foreign amount
        txn.amount_foreign = new_foreign
        db.add(txn)

    # 2) update any other fields (status, notes, etc.)
    update_data = data.dict(exclude_unset=True)
    update_data.pop("amount_foreign", None)
    for field, value in update_data.items():
        setattr(txn, field, value)

    # 3) commit & refresh, then log status if needed
    db.commit()
    db.refresh(txn)

    if "status" in data.dict(exclude_unset=True):
        from app.services.transactions_service import update_transaction_status
        update_transaction_status(
            db, txn.id, txn.status, txn.status_reason or "", modified_by
        )

    return txn

