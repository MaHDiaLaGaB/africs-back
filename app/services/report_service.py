from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, date
from app.models.transactions import Transaction
from app.models.receipt import ReceiptOrder
from app.models.transfer import TreasuryTransfer
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


def get_financial_report(db: Session, start_date, end_date, employee_id=None, country=None, service_name=None):
    query = db.query(Transaction).filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.status == "completed"
    )

    if employee_id:
        query = query.filter(Transaction.employee_id == employee_id)
    if service_name:
        query = query.join(Service).filter(Service.name == service_name)

    transactions = query.all()

    total_sent = sum(t.amount_foreign for t in transactions)
    total_lyd = sum(t.amount_lyd for t in transactions)

    total_cost = sum(t.amount_foreign * (t.currency.cost_per_unit if t.currency else 0) for t in transactions)
    profit = total_lyd - total_cost

    # ✅ التجميع حسب اليوم
    breakdown_query = (
    db.query(
        cast(Transaction.created_at, Date).label("date"),
        func.sum(Transaction.amount_lyd).label("total_lyd"),
        func.sum(Transaction.amount_foreign * Currency.cost_per_unit).label("total_cost")
    )
    .join(Currency, Transaction.currency_id == Currency.id)
    .filter(
        Transaction.created_at >= start_date,
        Transaction.created_at <= end_date,
        Transaction.status == "completed"
    )
    .group_by(cast(Transaction.created_at, Date))
    .order_by("date")
)


    if employee_id:
        breakdown_query = breakdown_query.filter(Transaction.employee_id == employee_id)
    if service_name:
        breakdown_query = breakdown_query.filter(Service.name == service_name)

    breakdown = breakdown_query.all()
    daily_breakdown = [
        {
            "date": str(row.date),
            "total_lyd": float(row.total_lyd),
            "total_profit": float(row.total_lyd - row.total_cost),
        }
        for row in breakdown
    ]

    return {
        "total_transactions": len(transactions),
        "total_sent_value": total_sent,
        "total_lyd_collected": total_lyd,
        "total_cost": total_cost,
        "total_profit": profit,
        "daily_breakdown": daily_breakdown,  # ✅ لتغذية الرسم البياني في الفرونتند
    }
