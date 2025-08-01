from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.transactions import Transaction, PaymentType, TransactionStatus
from app.schemas.transactions import TransactionCreate, TransactionUpdate
from app.models.customers import Customer
from app.models.currency import Currency
from app.models.service import Service
from app.models.users import User
from app.models.currency_lot import CurrencyLot
from app.services.treasury_service import adjust_employee_balance
from app.models.trnsx_status_log import TransactionStatusLog
from app.services.allocate_currency import allocate_and_compute
from app.models.transaction_currency_lot import TransactionCurrencyLot
from app.logger import Logger
from itertools import count

logger = Logger.get_logger(__name__)
_call_counter = count(1)

def generate_employee_reference(db: Session, employee: User) -> str:
    initials = f"{employee.full_name[0]}{employee.username[0]}".upper()
    count = db.query(Transaction).filter(Transaction.employee_id == employee.id).count()
    return f"{initials}{count + 1}"


def create_transaction(db: Session, data: TransactionCreate, employee: User) -> Transaction:
    service = (
        db.query(Service)
          .filter(Service.id == data.service_id, Service.is_active == True)
          .first()
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found or inactive")

    currency = (
        db.query(Currency)
          .filter(Currency.id == service.currency_id, Currency.is_active == True)
          .first()
    )
    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found or inactive")

    sale_rate = service.price if service.operation == "multiply" else 1.0 / service.price

    report = allocate_and_compute(
        db=db,
        currency=currency,
        needed_amount=data.amount_foreign,
        sale_rate=sale_rate
    )

    reference = generate_employee_reference(db, employee)
    txn = Transaction(
        reference       = reference,
        currency_id     = currency.id,
        service_id      = service.id,
        customer_name   = data.customer_name,
        to              = data.to,
        number          = data.number,
        amount_foreign  = data.amount_foreign,
        amount_lyd      = report["total_sale"],
        payment_type    = data.payment_type,
        profit          = report["profit"],
        employee_id     = employee.id,
        customer_id     = data.customer_id,
        status          = TransactionStatus.completed,
        notes           = data.notes,
    )
    db.add(txn)
    db.flush()

    for detail in report["breakdown"]:
        db.add(TransactionCurrencyLot(
            transaction_id = txn.id,
            lot_id         = detail["lot_id"],
            quantity       = detail["quantity"],
            cost_per_unit  = detail["unit_cost"],
        ))

    if data.payment_type == PaymentType.cash:
        adjust_employee_balance(db, employee.id, report["total_sale"])
    elif data.customer_id:
        customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer.balance_due += report["total_sale"]
        db.add(customer)

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
    call_id = next(_call_counter)
    logger.info("[%03d] ▶ Enter update_transaction_status", call_id)
    logger.info(
        "[%03d]     Params: transaction_id=%s, new_status=%s, reason=%r, modified_by=%s",
        call_id, transaction_id, new_status, reason, modified_by
    )

    logger.info("[%03d]     Querying Transaction.id=%s", call_id, transaction_id)
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        logger.warning("[%03d]     Transaction %s not found – aborting", call_id, transaction_id)
        raise HTTPException(status_code=404, detail="Transaction not found")

    old_status = txn.status
    logger.info("[%03d]     Loaded txn #%s with status=%s", call_id, txn.id, old_status)

    logger.info("[%03d]     Changing status → %s", call_id, new_status)
    txn.status = new_status
    txn.status_reason = reason

    if new_status == TransactionStatus.cancelled and old_status != TransactionStatus.cancelled:
        original_amount_lyd = txn.amount_lyd
        logger.info("[%03d]     Cancellation branch (original_amount_lyd=%s)", call_id, original_amount_lyd)

        if txn.payment_type == PaymentType.cash:
            logger.info(
                "[%03d]     Cash payment: refund employee %s by %s LYD",
                call_id, txn.employee_id, original_amount_lyd
            )
            adjust_employee_balance(db, txn.employee_id, -original_amount_lyd, call_id)

        elif txn.customer_id:
            logger.info("[%03d]     Adjusting customer #%s balance_due by -%s", call_id, txn.customer_id, original_amount_lyd)
            customer = db.query(Customer).filter(Customer.id == txn.customer_id).first()
            if customer:
                customer.balance_due -= original_amount_lyd
                db.add(customer)
            else:
                logger.warning("[%03d]     Customer %s not found – skipped balance adjustment", call_id, txn.customer_id)

        logger.info("[%03d]     Zeroing amounts: foreign & lyd", call_id)
        txn.amount_foreign = 0.0
        txn.amount_lyd     = 0.0

    log = TransactionStatusLog(
        transaction_id=txn.id,
        previous_status=old_status,
        new_status=new_status,
        reason=reason,
        changed_by=modified_by
    )
    logger.info("[%03d]     Creating TransactionStatusLog: %r", call_id, log)

    db.add(log)
    logger.info("[%03d]     Committing changes", call_id)
    db.commit()
    logger.info("[%03d]     Commit successful", call_id)

    db.refresh(txn)
    logger.info("[%03d]     Refreshed txn instance: %r", call_id, txn)
    logger.info("[%03d] ◀ Exit update_transaction_status (returned txn #%s)", call_id, txn.id)

    return txn


def update_transaction(
    db: Session,
    txn_id: int,
    data: TransactionUpdate,
    modified_by: int
) -> Transaction:
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # 1) detect foreign amount change
    if data.amount_foreign is not None and data.amount_foreign != txn.amount_foreign:
        old_foreign = txn.amount_foreign
        new_foreign = data.amount_foreign
        delta_foreign = new_foreign - old_foreign

        sale_rate = txn.service.price if txn.service.operation == "multiply" else 1.0 / txn.service.price

        if delta_foreign > 0:
            report = allocate_and_compute(db=db, currency=txn.currency, needed_amount=delta_foreign, sale_rate=sale_rate)
            for d in report["breakdown"]:
                db.add(TransactionCurrencyLot(transaction_id=txn.id, lot_id=d["lot_id"], quantity=d["quantity"], cost_per_unit=d["unit_cost"]))

            extra_sale = report["total_sale"]
            extra_profit = report["profit"]
            if txn.payment_type == PaymentType.cash:
                adjust_employee_balance(db, txn.employee_id, extra_sale)
            elif txn.customer_id:
                c = db.query(Customer).filter(Customer.id == txn.customer_id).first()
                if c:
                    c.balance_due += extra_sale
                    db.add(c)

            txn.amount_lyd += extra_sale
            txn.profit     += extra_profit

        else:
            to_release = -delta_foreign
            sale_to_deduct   = round(to_release * sale_rate, 2)
            profit_to_deduct = 0.0

            for detail in sorted(txn.lot_details, key=lambda d: d.id, reverse=True):
                if to_release <= 0:
                    break
                take = min(detail.quantity, to_release)
                cl = db.query(CurrencyLot).get(detail.lot_id)
                cl.remaining_quantity += take
                db.add(cl)

                profit_to_deduct += round(sale_rate * take - detail.cost_per_unit * take, 2)

                detail.quantity -= take
                if detail.quantity <= 0:
                    db.delete(detail)
                else:
                    db.add(detail)

                to_release -= take

            if txn.payment_type == PaymentType.cash:
                adjust_employee_balance(db, txn.employee_id, -sale_to_deduct)
            elif txn.customer_id:
                c = db.query(Customer).filter(Customer.id == txn.customer_id).first()
                if c:
                    c.balance_due -= sale_to_deduct
                    db.add(c)

            txn.amount_lyd -= sale_to_deduct
            txn.profit     -= profit_to_deduct

        txn.amount_foreign = new_foreign
        db.add(txn)

    # 2) update other fields, capture status change
    update_data = data.dict(exclude_unset=True)
    status = update_data.pop("status", None)
    reason = update_data.pop("status_reason", "")
    update_data.pop("amount_foreign", None)

    for field, value in update_data.items():
        setattr(txn, field, value)

    # 3) commit & refresh base transaction updates
    db.commit()
    db.refresh(txn)

    # 4) handle status update via dedicated helper
    if status is not None and status != txn.status:
        txn = update_transaction_status(
            db,
            txn.id,
            status,
            reason,
            modified_by
        )

    return txn
