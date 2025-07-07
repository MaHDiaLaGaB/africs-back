from fastapi import HTTPException
from app.models.currency import Currency
from sqlalchemy.orm import Session
from typing import List, Dict

def allocate_currency_lots(db: Session, currency: Currency, needed_amount: float):
    """
    يختار دفعات العملة الأقدم أولاً حتى يغطي 'needed_amount'.
    يُقلل remaining_quantity في كل دفعة ويُرجع قائمة بالتخصيصات.
    """
    remaining = needed_amount
    allocations = []  # [(lot, qty_consumed), ...]

    # نرتب الدفعات حسب التاريخ الأقدم أولاً
    for lot in sorted(currency.lots, key=lambda l: l.created_at):
        if lot.remaining_quantity <= 0:
            continue
        take = min(lot.remaining_quantity, remaining)
        allocations.append((lot, take))
        remaining -= take
        if remaining <= 0:
            break

    if remaining > 0:
        raise HTTPException(status_code=400, detail="Insufficient currency stock")

    # تحديث الكميات المتبقية في الدفعات
    for lot, qty in allocations:
        lot.remaining_quantity -= qty
        db.add(lot)

    return allocations


def allocate_and_compute(
    db: Session,
    currency,             # كائن Currency
    needed_amount: float, # الكمية المطلوبة
    sale_rate: float      # سعر البيع لكل وحدة بالليرة
) -> Dict:
    """
    1) يخصص الكمية المطلوبة FIFO من دفعات العملة.
    2) يحسب تكلفة الشراء لكل دفعة، ومتوسط التكلفة،
       ويحسب إجمالي البيع وصافي الربح.
    """
    # 1. جلب التخصيص (lot, qty)
    allocations = allocate_currency_lots(db, currency, needed_amount)

    # 2. بناء تفصيل التخصيص واحتساب التكلفة
    breakdown: List[Dict] = []
    total_cost = 0.0
    for lot, qty in allocations:
        cost = lot.cost_per_unit * qty
        breakdown.append({
            "lot_id": lot.id,
            "unit_cost": lot.cost_per_unit,
            "quantity": qty,
            "cost": round(cost, 2)
        })
        total_cost += cost

    # 3. متوسط تكلفة الوحدة (weighted average)
    avg_cost = round(total_cost / needed_amount, 4)

    # 4. إجمالي البيع وصافي الربح
    total_sale = round(needed_amount * sale_rate, 2)
    profit = round(total_sale - total_cost, 2)

    return {
        "breakdown": breakdown,
        "total_cost": round(total_cost, 2),
        "avg_cost": avg_cost,
        "total_sale": total_sale,
        "profit": profit,
    }
