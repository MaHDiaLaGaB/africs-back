from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, date
from app.models.transactions import Transaction
from app.models.receipt import ReceiptOrder
from app.models.transfer import TreasuryTransfer
from app.models.transaction_currency_lot import TransactionCurrencyLot
from app.models import Service, Currency


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
    country: str = None,       # if you someday want to filter by country
    service_name: str = None,
):
    # 1) Base transaction query
    txn_q = (
        db.query(Transaction)
        .filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date,
            Transaction.status == "completed",
        )
    )
    if employee_id:
        txn_q = txn_q.filter(Transaction.employee_id == employee_id)
    if service_name:
        txn_q = txn_q.join(Service).filter(Service.name == service_name)

    transactions = txn_q.all()

    # 2) Totals in Python (uses each txn.lot_details list):
    total_sent    = sum(t.amount_foreign for t in transactions)
    total_lyd     = sum(t.amount_lyd     for t in transactions)
    total_cost    = 0.0
    for t in transactions:
        # sum up cost-per-unit * quantity across all lots in that txn
        total_cost += sum(
            lot.quantity * lot.cost_per_unit for lot in t.lot_details
        )
    total_profit = total_lyd - total_cost

    # 3) Daily breakdown via SQL, joining through TransactionCurrencyLot
    breakdown_q = (
        db.query(
            cast(Transaction.created_at, Date).label("date"),
            func.sum(Transaction.amount_lyd).label("total_lyd"),
            func.sum(
                TransactionCurrencyLot.quantity * TransactionCurrencyLot.cost_per_unit
            ).label("total_cost"),
        )
        .join(
            TransactionCurrencyLot,
            Transaction.id == TransactionCurrencyLot.transaction_id,
        )
        .filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date,
            Transaction.status == "completed",
        )
        .group_by(cast(Transaction.created_at, Date))
        .order_by(cast(Transaction.created_at, Date))
    )
    if employee_id:
        breakdown_q = breakdown_q.filter(Transaction.employee_id == employee_id)
    if service_name:
        # make sure to join Service before filtering
        breakdown_q = breakdown_q.join(Service).filter(Service.name == service_name)

    daily_rows = breakdown_q.all()
    daily_breakdown = [
        {
            "date":          str(r.date),
            "total_lyd":     float(r.total_lyd or 0),
            "total_profit":  float((r.total_lyd or 0) - (r.total_cost or 0)),
        }
        for r in daily_rows
    ]

    return {
        "total_transactions":    len(transactions),
        "total_sent_value":      float(total_sent),
        "total_lyd_collected":   float(total_lyd),
        "total_cost":            float(total_cost),
        "total_profit":          float(total_profit),
        "daily_breakdown":       daily_breakdown,
    }