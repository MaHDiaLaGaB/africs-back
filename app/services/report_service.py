from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, time
from app.models.transactions import Transaction
from app.models.receipt import ReceiptOrder
from app.models.transfer import TreasuryTransfer
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import joinedload
from datetime import datetime, time
from app.schemas.transactions import TransactionStatus
from app.models import Service
from app.logger import Logger

logger = Logger.get_logger(__name__)


def get_daily_summary(db: Session, employee_id: int, for_date: date):
    start = datetime.combine(for_date, datetime.min.time())
    end = datetime.combine(for_date, datetime.max.time())

    cash_txns = (
        db.query(Transaction)
        .filter(
            Transaction.employee_id == employee_id,
            Transaction.payment_type == "cash",
            Transaction.created_at.between(start, end),
        )
        .all()
    )

    receipts = (
        db.query(ReceiptOrder)
        .filter(
            ReceiptOrder.employee_id == employee_id,
            ReceiptOrder.created_at.between(start, end),
        )
        .all()
    )

    transfers = (
        db.query(TreasuryTransfer)
        .filter(
            TreasuryTransfer.from_employee_id == employee_id,
            TreasuryTransfer.created_at.between(start, end),
        )
        .all()
    )

    return {
        "cash_transactions": cash_txns,
        "receipts": receipts,
        "transfers": transfers,
    }


# def compute_expected_lyd(amount_foreign: float, service: Service) -> float:
#     """
#     For multiply: foreign * price
#     For divide: foreign * price / 100 (per your semantics)
#     """
#     if service.operation == "multiply":
#         return round(amount_foreign * service.price, 2)
#     elif service.operation == "divide":
#         return round(amount_foreign * service.price / 100.0, 2)
#     else:
#         raise ValueError(f"Unsupported operation {service.operation}")



# from decimal import Decimal, ROUND_HALF_UP
# from datetime import datetime, time
# from sqlalchemy.orm import joinedload, Session
# from app.models.transactions import Transaction, TransactionStatus
from app.services.allocate_currency import allocate_and_compute
# from app.schemas.transactions import TransactionCreate, TransactionUpdate
# from app.models.currency import Currency
# from app.models.service import Service
# from app.logger import Logger

logger = Logger.get_logger(__name__)

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, time
from typing import Optional
to_import = ["Session"]  # ensure SQLAlchemy Session import
from sqlalchemy.orm import joinedload, Session
from app.models.transactions import Transaction, TransactionStatus
from app.models.service import Service
from app.services.allocate_currency import allocate_and_compute
from app.logger import Logger

logger = Logger.get_logger(__name__)


def quantize(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_expected_lyd(amount_foreign: Decimal, service) -> Decimal:
    price = Decimal(str(service.price))
    op = service.operation
    if op == "multiply":
        return quantize(amount_foreign * price)
    elif op == "divide":
        if price == 0:
            raise ValueError("Division by zero in rate")
        return quantize(amount_foreign / price)
    elif op == "plus":  # head-to-head
        return quantize(amount_foreign)
    else:
        raise ValueError(f"Unsupported operation {op}")


def get_financial_report(
    db: Session,
    start_date: date,
    end_date: date,
    employee_id: Optional[int] = None,
    country: Optional[str] = None,
    service_name: Optional[str] = None,
):
    logger.info(
        "Entering get_financial_report: start_date=%s, end_date=%s, employee_id=%s, service_name=%s, country=%s",
        start_date, end_date, employee_id, service_name, country
    )

    start_dt = datetime.combine(start_date, time.min)
    end_dt   = datetime.combine(end_date, time.max)

    # Build filters
    filters = [
        Transaction.created_at >= start_dt,
        Transaction.created_at <= end_dt,
        Transaction.status == TransactionStatus.completed,
    ]
    if employee_id:
        filters.append(Transaction.employee_id == employee_id)
    if service_name:
        filters.append(Transaction.service.has(name=service_name))
    if country:
        filters.append(Transaction.service.has(Service.country.has(name=country)))

    # Eager-load
    transactions = (
        db.query(Transaction)
          .options(joinedload(Transaction.service))
          .filter(*filters)
          .all()
    )
    logger.info("Fetched %d completed transactions", len(transactions))

    total_sent = Decimal("0")
    total_lyd = Decimal("0")
    total_cost_from_lots = Decimal("0")
    total_profit_computed = Decimal("0")
    total_profit_stored = Decimal("0")

    daily_aggregate: dict = {}

    for t in transactions:
        amt_foreign = Decimal(str(t.amount_foreign or 0))
        lyd_collected = Decimal(str(t.amount_lyd or 0))
        stored_profit = Decimal(str(t.profit or 0))

        op = t.service.operation
        # Determine sale_rate
        if op in ("multiply", "divide"):
            sale_rate = float(t.service.price)
        elif op == "pluse":
            sale_rate = 1.0
        else:
            logger.error("Unsupported operation %s on txn %s", op, t.id)
            continue

        alloc = allocate_and_compute(
            db=db,
            currency=t.service.currency,
            needed_amount=float(amt_foreign),
            sale_rate=sale_rate,
            operation=op
        )
        cost_from_lots = quantize(Decimal(str(alloc["total_cost"])))
        profit_computed = quantize(Decimal(str(alloc["profit"])))

        # LYD mismatch
        try:
            expected = compute_expected_lyd(amt_foreign, t.service)
            if abs(expected - lyd_collected) > Decimal("0.5"):
                logger.warning(
                    "Txn #%s LYD mismatch: expected %s vs stored %s",
                    t.id, expected, lyd_collected
                )
        except Exception:
            logger.debug("Skipping LYD check for txn #%s", t.id)

        # cost drift
        implied = quantize(lyd_collected - stored_profit)
        if abs(implied - cost_from_lots) > Decimal("0.5"):
            logger.warning(
                "Txn #%s cost drift: implied %s vs allocated %s",
                t.id, implied, cost_from_lots
            )

        total_sent += amt_foreign
        total_lyd += lyd_collected
        total_cost_from_lots += cost_from_lots
        total_profit_computed += profit_computed
        total_profit_stored += stored_profit

        day = t.created_at.date()
        if day not in daily_aggregate:
            daily_aggregate[day] = {"total_lyd": Decimal("0"), "total_profit": Decimal("0")}
        daily_aggregate[day]["total_lyd"] += lyd_collected
        daily_aggregate[day]["total_profit"] += profit_computed

    total_cost = quantize(total_lyd - total_profit_computed)
    if abs(total_cost - total_cost_from_lots) > Decimal("1.0"):
        logger.warning(
            "Aggregate cost divergence: computed %s vs lots-based %s",
            total_cost, total_cost_from_lots
        )

    daily_breakdown = []
    for day in sorted(daily_aggregate):
        lyd = quantize(daily_aggregate[day]["total_lyd"])
        profit = quantize(daily_aggregate[day]["total_profit"])
        cost = quantize(lyd - profit)
        daily_breakdown.append({
            "date": str(day),
            "total_lyd": float(lyd),
            "total_profit": float(profit),
            "total_cost": float(cost),
        })
        logger.debug("Daily %s -> lyd %s, profit %s, cost %s", day, lyd, profit, cost)

    return {
        "total_transactions": len(transactions),
        "total_sent_value": float(quantize(total_sent)),
        "total_lyd_collected": float(quantize(total_lyd)),
        "total_cost": float(total_cost),
        "total_profit": float(quantize(total_profit_computed)),
        "total_profit_stored": float(quantize(total_profit_stored)),
        "daily_breakdown": daily_breakdown,
    }
