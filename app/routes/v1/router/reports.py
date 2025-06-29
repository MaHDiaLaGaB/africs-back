from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, datetime
from app.services.report_service import get_financial_report
from app.dependencies import get_db
from app.models.transactions import Transaction
from app.models.service import Service
from app.models.users import User
from app.models.currency import Currency

router = APIRouter()


@router.get("/financial-report")
def financial_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    employee_id: int = None,
    country: str = None,
    service_name: str = None,
    db: Session = Depends(get_db),
):
    return get_financial_report(
        db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        country=country,
        service_name=service_name,
    )


@router.get("/overview")
def get_admin_dashboard_data(db: Session = Depends(get_db)):
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end   = datetime.combine(today, datetime.max.time())

    today_txns       = db.query(Transaction).filter(Transaction.created_at.between(start, end)).all()
    total_lyd_today  = sum(t.amount_lyd     for t in today_txns)
    total_for_today  = sum(t.amount_foreign for t in today_txns)
    total_txns_today = len(today_txns)

    profit_today = sum(
        (t.currency.exchange_rate - t.currency.cost_per_unit) * t.amount_foreign
        for t in today_txns if t.currency
    )

    raw_top_emps = (
        db.query(User.username, func.sum(Transaction.amount_lyd).label("total"))
          .join(Transaction)
          .group_by(User.id)
          .order_by(desc("total"))
          .limit(5)
          .all()
    )
    raw_top_svcs = (
        db.query(Service.name, func.count(Transaction.id).label("count"))
          .join(Transaction)
          .group_by(Service.id)
          .order_by(desc("count"))
          .limit(5)
          .all()
    )
    raw_top_cur = (
        db.query(Currency.name, func.sum(Transaction.amount_foreign).label("used"))
          .join(Transaction)
          .group_by(Currency.id)
          .order_by(desc("used"))
          .limit(5)
          .all()
    )

    # convert to serializable lists of dicts
    top_employees = [{"username": u, "total": float(t)} for u, t in raw_top_emps]
    top_services  = [{"service_name": name, "count": int(c)} for name, c in raw_top_svcs]
    top_currencies= [{"currency": name, "used": float(u)} for name, u in raw_top_cur]

    return {
        "total_txns_today":     total_txns_today,
        "total_lyd_today":      float(total_lyd_today),
        "total_foreign_today":  float(total_for_today),
        "profit_today":         float(profit_today),
        "top_employees":        top_employees,
        "top_services":         top_services,
        "top_currencies":       top_currencies,
    }

