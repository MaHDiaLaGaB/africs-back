from fastapi import HTTPException
from app.models.currency import Currency
from sqlalchemy.orm import Session

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
