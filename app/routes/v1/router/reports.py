from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import date, datetime
from app.services.report_service import get_financial_report
from app.dependencies import get_db
from app.models.transactions import Transaction
from app.models.service import Service
from app.models.users import User
from app.models.currency import Currency
from app.models.transaction_report import TransactionReport
from app.schemas.transaction_report import TransactionReportOut
from app.core.security import get_current_user

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



@router.get(
    "/transaction-report",
    response_model=List[TransactionReportOut],
    summary="تقارير تحويلات الموظف/الإدارة",
    description="يُرجِع قائمة تحويلات موسّعة مع تفاصيل العميل والخدمة والعملات."
)
def read_transaction_reports(
    db: Session              = Depends(get_db),
    current_user: User       = Depends(get_current_user),
    skip: int                = Query(0,  ge=0,  description="الإزاحة"),
    limit: int               = Query(100, ge=1, le=500, description="عدد النتائج"),
    employee_id: Optional[int] = Query(None, description="فلترة موظّف (Admins only)"),
):
    """
    - الموظف: يرى تحويلاته فقط، ولا يُسمح بتمرير employee_id.
    - المدير: يستطيع تمرير employee_id أو تركه لجلب جميع الموظفين.
    """
    query = db.query(TransactionReport)

    # 🛡️ حماية: الموظف لا يرى سوا معاملاتـه
    if current_user.role == "employee":
        query = query.filter(TransactionReport.employee_id == current_user.id)

    # مدير يطلب موظفًا محددًا
    elif employee_id is not None:
        query = query.filter(TransactionReport.employee_id == employee_id)

    # (اختيارى) يمكن إضافة فلاتر حالة أو تاريخ هنا …

    return (
        query
        .order_by(TransactionReport.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )