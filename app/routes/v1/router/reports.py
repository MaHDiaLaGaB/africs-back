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
    end = datetime.combine(today, datetime.max.time())

    # إحصائيات اليوم
    today_txns = db.query(Transaction).filter(Transaction.created_at.between(start, end)).all()
    total_lyd_today = sum(t.amount_lyd for t in today_txns)
    total_foreign_today = sum(t.amount_foreign for t in today_txns)
    total_txns_today = len(today_txns)

    # إجمالي الربح = (سعر البيع - سعر التكلفة) × كمية
    profit_today = sum(
        ((t.currency.exchange_rate - t.currency.cost_per_unit) * t.amount_foreign)
        for t in today_txns if t.currency
    )

    # أفضل الموظفين حسب المبيعات
    top_employees = (
        db.query(User.username, func.sum(Transaction.amount_lyd).label("total"))
        .join(Transaction)
        .group_by(User.id)
        .order_by(desc("total"))
        .limit(5)
        .all()
    )

    # أكثر الخدمات استخدامًا
    top_services = (
        db.query(Service.name, func.count(Transaction.id).label("count"))
        .join(Transaction)
        .group_by(Service.id)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    # أكثر العملات استخدامًا
    top_currencies = (
        db.query(Currency.name, func.sum(Transaction.amount_foreign).label("used"))
        .join(Transaction)
        .group_by(Currency.id)
        .order_by(desc("used"))
        .limit(5)
        .all()
    )

    return {
        "total_txns_today": total_txns_today,
        "total_lyd_today": total_lyd_today,
        "total_foreign_today": total_foreign_today,
        "profit_today": profit_today,
        "top_employees": top_employees,
        "top_services": top_services,
        "top_currencies": top_currencies,
    }
