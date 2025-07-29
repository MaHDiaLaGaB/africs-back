from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, date, time
from app.models.transactions import Transaction
from app.models.receipt import ReceiptOrder
from app.models.transfer import TreasuryTransfer
from app.models.transaction_currency_lot import TransactionCurrencyLot
from app.models import Service, Currency
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


def get_financial_report(
    db: Session,
    start_date: date,
    end_date: date,
    employee_id: int = None,
    country: str = None,
    service_name: str = None,
):
    """
    Returns aggregate financial report and daily breakdown.
    Debug logs added to trace values and SQL.
    """
    logger.info(
        "Entering get_financial_report: start_date=%s, end_date=%s, employee_id=%s, service_name=%s",
        start_date, end_date, employee_id, service_name
    )

    # Convert to full day range
    start_dt = datetime.combine(start_date, time.min)
    end_dt   = datetime.combine(end_date,   time.max)
    logger.debug("Using datetime range %s to %s", start_dt, end_dt)

    # 1) Base transaction query
    txn_q = (
        db.query(Transaction)
        .filter(
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
            Transaction.status == "completed",
        )
    )
    if employee_id:
        txn_q = txn_q.filter(Transaction.employee_id == employee_id)
    if service_name:
        txn_q = txn_q.join(Service).filter(Service.name == service_name)
    logger.debug("Transaction query SQL: %s", str(txn_q))

    transactions = txn_q.all()
    logger.info("Fetched %d completed transactions", len(transactions))

    # 2) Compute totals in Python
    total_sent = sum(t.amount_foreign for t in transactions)
    total_lyd  = sum(t.amount_lyd for t in transactions)
    total_cost = 0.0
    for t in transactions:
        cost = sum(lot.quantity * lot.cost_per_unit for lot in t.lot_details)
        total_cost += cost
        logger.debug("Transaction %s cost: %s", t.id, cost)
    total_profit = total_lyd - total_cost
    logger.info("Totals -> sent: %s, lyd: %s, cost: %s, profit: %s",
                total_sent, total_lyd, total_cost, total_profit)

    # 3) Daily breakdown
    breakdown_q = (
        db.query(
            cast(Transaction.created_at, Date).label("date"),
            func.sum(Transaction.amount_lyd).label("total_lyd"),
            func.sum(
                TransactionCurrencyLot.quantity * TransactionCurrencyLot.cost_per_unit
            ).label("total_cost"),
        )
        .join(TransactionCurrencyLot, Transaction.id == TransactionCurrencyLot.transaction_id)
        .filter(
            Transaction.created_at >= start_dt,
            Transaction.created_at <= end_dt,
            Transaction.status == "completed",
        )
    )
    if employee_id:
        breakdown_q = breakdown_q.filter(Transaction.employee_id == employee_id)
    if service_name:
        breakdown_q = breakdown_q.join(Service).filter(Service.name == service_name)
    logger.debug("Daily breakdown query SQL: %s", str(breakdown_q))

    daily_rows = breakdown_q.group_by(cast(Transaction.created_at, Date)) \
                          .order_by(cast(Transaction.created_at, Date)) \
                          .all()
    logger.info("Fetched %d daily rows", len(daily_rows))

    daily_breakdown = []
    for r in daily_rows:
        ly = float(r.total_lyd or 0)
        co = float(r.total_cost or 0)
        pf = ly - co
        daily_breakdown.append({
            "date": str(r.date),
            "total_lyd": ly,
            "total_profit": pf,
        })
        logger.debug("Daily %s -> lyd: %s, profit: %s", r.date, ly, pf)

    result = {
        "total_transactions": len(transactions),
        "total_sent_value": float(total_sent),
        "total_lyd_collected": float(total_lyd),
        "total_cost": float(total_cost),
        "total_profit": float(total_profit),
        "daily_breakdown": daily_breakdown,
    }
    logger.info("get_financial_report result: %s", result)
    return result